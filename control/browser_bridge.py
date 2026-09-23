# Thin V13 wrapper around the preserved browser bridge implementation.
# The original implementation is stored byte-for-byte in browser_bridge_core.py.
# Executing it in this module's globals preserves monkeypatch/test semantics while
# letting the AI-response channel stay separate from the generic executor route.

import os as _bridge_os
from pathlib import Path as _WrapperPath

_wrapper_name = globals().get("__name__", "browser_bridge")
_core_path = _WrapperPath(__file__).with_name("browser_bridge_core.py")
_core_source = _core_path.read_text(encoding="utf-8")
globals()["__name__"] = "prediction_research_browser_bridge_core"
exec(compile(_core_source, str(_core_path), "exec"), globals(), globals())
globals()["__name__"] = _wrapper_name

_CoreHandler = Handler
_core_next_outbox_item = next_outbox_item
_core_next_ai_outbox_item = next_ai_outbox_item
_core_acknowledge_ai = acknowledge_ai
_core_acknowledge = acknowledge
_core_enqueue = enqueue
_core_commit_and_push = commit_and_push

from executor_preflight import sync_main_fail_closed as _sync_main_fail_closed


CLIENT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{2,159}$")
CONSUMER_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{2,199}$")
RESULT_LEASE_SECONDS = 45.0
AI_LEASE_SECONDS = 90.0


# Capture the exact repository revision whose Python source is currently loaded
# in this long-running bridge process. A later git fast-forward changes files on
# disk but does not change already-imported Python code, so execution must fail
# closed until this process has re-execed itself.
_loaded_probe = git("rev-parse", "HEAD", check=False)
_LOADED_BRIDGE_COMMIT = (
    _loaded_probe.stdout.strip()
    if _loaded_probe.returncode == 0
    else ""
)
_BRIDGE_REEXEC_SCHEDULED = False


def _current_head() -> str:
    probe = git("rev-parse", "HEAD", check=False)
    return probe.stdout.strip() if probe.returncode == 0 else ""


def _reexec_bridge_runtime() -> None:
    """Replace this process with the current on-disk bridge implementation."""
    script = str(_WrapperPath(__file__).resolve())
    _bridge_os.execv(sys.executable, [sys.executable, script])


def _schedule_bridge_reexec() -> None:
    """Schedule re-exec after the current HTTP response has had time to flush."""
    global _BRIDGE_REEXEC_SCHEDULED
    if _BRIDGE_REEXEC_SCHEDULED:
        return
    _BRIDGE_REEXEC_SCHEDULED = True
    timer = threading.Timer(0.35, _reexec_bridge_runtime)
    timer.daemon = True
    timer.start()


def _safe_client_id(value) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if not CLIENT_ID_RE.fullmatch(text):
        return None
    return text


def _safe_consumer_id(value) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if not CONSUMER_ID_RE.fullmatch(text):
        return None
    return text


def _route_for_task(state: dict, task_id: str) -> str | None:
    routes = state.get("task_clients")
    if isinstance(routes, dict):
        value = _safe_client_id(routes.get(task_id))
        if value:
            return value

    incident_routes = state.get("incident_clients")
    if isinstance(incident_routes, dict):
        value = _safe_client_id(incident_routes.get(task_id))
        if value:
            return value

    return None


def _bind_task_client(
    state: dict,
    task_id: str,
    client_id: str | None,
) -> dict | None:
    if client_id is None:
        return None

    routes = state.setdefault("task_clients", {})
    existing = _safe_client_id(routes.get(task_id))

    if existing and existing != client_id:
        return {
            "ok": False,
            "error": "task client conflict",
            "reason": "TASK_CLIENT_CONFLICT",
            "task_id": task_id,
        }

    routes[task_id] = client_id
    return None


def _lease_result(
    state: dict,
    task_id: str,
    client_id: str | None,
    consumer_id: str | None,
) -> bool:
    if client_id is None:
        return True

    consumer = consumer_id or client_id
    leases = state.setdefault("result_delivery_leases", {})
    now = time.time()
    existing = leases.get(task_id)

    if isinstance(existing, dict):
        try:
            lease_until = float(existing.get("lease_until") or 0)
        except (TypeError, ValueError):
            lease_until = 0

        existing_client = _safe_client_id(existing.get("client_id"))
        existing_consumer = _safe_consumer_id(existing.get("consumer_id"))

        if lease_until > now:
            if existing_client != client_id:
                return False
            if existing_consumer and existing_consumer != consumer:
                return False

    leases[task_id] = {
        "client_id": client_id,
        "consumer_id": consumer,
        "leased_at": now,
        "lease_until": now + RESULT_LEASE_SECONDS,
    }
    return True


def _read_result_item(task_id: str, *, detail: str) -> dict | None:
    result_dir = RESULTS / task_id
    result_file = result_dir / "RESULT.json"
    if not result_file.exists():
        return None

    result = json.loads(result_file.read_text())
    stdout_file = result_dir / "stdout.log"
    stderr_file = result_dir / "stderr.log"

    lifecycle_update(task_id, "DELIVERED", detail)

    return {
        "task_id": task_id,
        "result": result,
        "stdout": (
            stdout_file.read_text(errors="replace")[:20000]
            if stdout_file.exists()
            else ""
        ),
        "stderr": (
            stderr_file.read_text(errors="replace")[:20000]
            if stderr_file.exists()
            else ""
        ),
        "git_head": git(
            "rev-parse",
            "--short",
            "HEAD",
        ).stdout.strip(),
    }


def _incident_outbox_id(path: _WrapperPath) -> str:
    raw = "INCIDENT-" + path.stem

    return "".join(
        ch
        if ch.isalnum() or ch in "._:-"
        else "_"
        for ch in raw
    )[:150]


def _next_incident_item(
    state: dict,
    acked: set[str],
    client_id: str | None,
    consumer_id: str | None,
) -> dict | None:
    incident_dir = (
        _WrapperPath.home()
        / ".local"
        / "state"
        / "prediction-research"
        / "incidents"
    )
    if not incident_dir.exists():
        return None

    routes = state.setdefault("incident_clients", {})

    for incident_path in sorted(
        incident_dir.glob("*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    ):
        try:
            incident = json.loads(
                incident_path.read_text(encoding="utf-8")
            )
        except Exception:
            continue

        if not incident.get("deliver_to_chat"):
            continue
        if incident.get("status") != "OPEN":
            continue
        if incident.get("reason") == "HOURLY_RESEARCH_WAKE":
            continue

        task_id = _incident_outbox_id(incident_path)
        if task_id in acked:
            continue

        route = _safe_client_id(routes.get(task_id))

        if client_id is None:
            if route is not None:
                continue
        else:
            if route is None:
                routes[task_id] = client_id
                route = client_id
            if route != client_id:
                continue

        if not _lease_result(
            state,
            task_id,
            client_id,
            consumer_id,
        ):
            continue

        bridge_tasks = state.setdefault("bridge_tasks", [])
        if task_id not in bridge_tasks:
            bridge_tasks.append(task_id)

        head = git(
            "rev-parse",
            "--short",
            "HEAD",
        ).stdout.strip()

        lifecycle_update(
            task_id,
            "DELIVERED",
            "bridge routed incident to chat client",
        )

        state["outbox_prefer_incident"] = False
        save_state(state)

        result = {
            "task_id": task_id,
            "hypothesis_id": "CONTROL-NO-SILENT-WAITING",
            "task_class": "infrastructure",
            "status": "incident",
            "source_commit": head,
            "started_at": None,
            "finished_at": None,
            "exit_code": None,
            "command": [],
            "incident": incident,
        }

        return {
            "task_id": task_id,
            "result": result,
            "stdout": json.dumps(
                incident,
                indent=2,
                sort_keys=True,
            ),
            "stderr": "",
            "git_head": head,
        }

    return None


def next_outbox_item(
    client_id: str | None = None,
    consumer_id: str | None = None,
) -> dict | None:
    """Return only work routed to the requesting chat client.

    A client-less legacy browser receives only legacy/unrouted work. That keeps
    a still-running old extension compatible during a rolling upgrade without
    allowing it to steal a result already bound to another chat.
    """

    client_id = _safe_client_id(client_id)
    consumer_id = _safe_consumer_id(consumer_id)

    state = load_state()
    bridge_tasks = list(state.get("bridge_tasks", []))
    acked = set(state.get("acked", []))

    recovered = False
    for task_id in bridge_tasks:
        try:
            lifecycle = lifecycle_load(task_id)
        except Exception:
            continue
        if lifecycle.get("state") == "ACKED" and task_id not in acked:
            acked.add(task_id)
            recovered = True

    if recovered:
        state["acked"] = sorted(acked)
        save_state(state)

    for task_id in reversed(bridge_tasks):
        if task_id in acked:
            continue

        route = _route_for_task(state, task_id)
        if client_id is None:
            if route is not None:
                continue
        elif route != client_id:
            continue

        result_file = RESULTS / task_id / "RESULT.json"
        if not result_file.exists():
            continue

        if not _lease_result(
            state,
            task_id,
            client_id,
            consumer_id,
        ):
            continue

        save_state(state)
        return _read_result_item(
            task_id,
            detail="bridge routed result to chat client",
        )

    return _next_incident_item(
        state,
        acked,
        client_id,
        consumer_id,
    )


def commit_and_push(message: str, stage_paths=None):
    """A bridge enqueue is durable only when its commit reached origin/main.

    The historical core intentionally kept local evidence when a push failed,
    but returned success to enqueue. That can create a local-only task on a
    stale branch. Preserve the local commit, but fail closed so the task is not
    ACCEPTED until synchronization/publishing succeeds on a later retry.
    """
    committed, detail = _core_commit_and_push(message, stage_paths)
    if committed and "remote push failed" in str(detail).lower():
        return False, detail
    return committed, detail


def enqueue(envelope, client_id: str | None = None):
    """Synchronize, route and attest the bridge runtime before accepting a task."""
    client_id = _safe_client_id(client_id)

    with LOCK:
        sync = _sync_main_fail_closed(ROOT)
        if not sync.get("ok"):
            reason = str(sync.get("reason") or "BRIDGE_PREFLIGHT_SYNC_BLOCKED")
            print(f"[bridge] enqueue preflight blocked reason={reason}")
            return {
                "ok": False,
                "error": "bridge checkout preflight blocked",
                "reason": reason,
                "sync": sync,
                "recoverable": True,
                "queue_status": queue_status(),
            }

        current_head = _current_head()
        if (
            not _LOADED_BRIDGE_COMMIT
            or not current_head
            or current_head != _LOADED_BRIDGE_COMMIT
        ):
            print(
                "[bridge] stale runtime blocked; "
                f"loaded={_LOADED_BRIDGE_COMMIT or 'UNKNOWN'} "
                f"current={current_head or 'UNKNOWN'}"
            )
            _schedule_bridge_reexec()
            return {
                "ok": False,
                "error": "bridge runtime stale after repository sync",
                "reason": "BRIDGE_RUNTIME_STALE_REEXEC_SCHEDULED",
                "loaded_commit": _LOADED_BRIDGE_COMMIT or None,
                "current_head": current_head or None,
                "recoverable": True,
                "queue_status": queue_status(),
            }

        if client_id is not None:
            state = load_state()
            conflict = _bind_task_client(
                state,
                envelope.task.task_id,
                client_id,
            )
            if conflict is not None:
                return conflict
            save_state(state)

        result = _core_enqueue(envelope)
        if client_id is not None:
            result = dict(result)
            result["client_id"] = client_id
        return result


# An AI prompt is ACKed after it is inserted into ChatGPT. If the assistant
# response is then lost before /ai-response is received, the old core would
# suppress that hourly bundle forever. Retry only bundles that this V13 wrapper
# itself timestamped; legacy ACKs without delivery metadata are never replayed.
AI_RETRY_AFTER_SECONDS = 600


def _hourly_incident_for_task(task_id: str):
    incident_dir = (
        _WrapperPath.home()
        / ".local"
        / "state"
        / "prediction-research"
        / "incidents"
    )
    if not incident_dir.exists():
        return None

    for path in incident_dir.glob("*__HOURLY_RESEARCH_WAKE.json"):
        try:
            incident = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if str(incident.get("task_id") or "") == task_id:
            return incident
    return None


def _valid_ai_item(item) -> bool:
    if not isinstance(item, dict):
        return False
    forbidden = {"command", "shell", "argv", "exec", "executable"}
    if forbidden.intersection(item):
        return False
    if item.get("kind") != "AI_WORK_BUNDLE":
        return False
    guardrails = item.get("guardrails") or {}
    return guardrails.get("direct_executor_route") is False


def _stalled_ai_retry(state: dict):
    deliveries = state.get("ai_deliveries")
    if not isinstance(deliveries, dict):
        return None

    acked = set(state.get("ai_acked", []))
    now = time.time()
    candidates = []

    for task_id, meta in deliveries.items():
        if task_id not in acked or not isinstance(meta, dict):
            continue
        try:
            last_acked_at = float(meta.get("last_acked_at"))
        except (TypeError, ValueError):
            continue
        if now - last_acked_at < AI_RETRY_AFTER_SECONDS:
            continue
        candidates.append((last_acked_at, str(task_id)))

    for _, task_id in sorted(candidates):
        incident = _hourly_incident_for_task(task_id)
        if incident is None:
            continue
        if not AI_TRANSPORT.should_offer_ai_work(incident):
            continue
        try:
            item = AI_TRANSPORT.build_chat_item(incident)
        except Exception:
            continue
        if _valid_ai_item(item):
            return item

    return None


def _ai_item_route(state: dict, item: dict) -> str | None:
    bundle = item.get("bundle")
    if not isinstance(bundle, dict):
        return None

    source_task_id = str(bundle.get("source_task_id") or "")
    if not source_task_id:
        return None

    return _route_for_task(state, source_task_id)


def next_ai_outbox_item(
    client_id: str | None = None,
    consumer_id: str | None = None,
):
    client_id = _safe_client_id(client_id)
    consumer_id = _safe_consumer_id(consumer_id)

    state = load_state()
    retry = _stalled_ai_retry(state)
    item = retry if retry is not None else _core_next_ai_outbox_item()
    if item is None:
        return None

    task_id = str(item.get("task_id") or "")
    if not task_id:
        return None

    route = _ai_item_route(state, item)
    if route is not None and client_id != route:
        return None

    leases = state.setdefault("ai_delivery_leases", {})
    now = time.time()
    existing = leases.get(task_id)

    if isinstance(existing, dict):
        try:
            lease_until = float(existing.get("lease_until") or 0)
        except (TypeError, ValueError):
            lease_until = 0

        if lease_until > now:
            existing_client = _safe_client_id(existing.get("client_id"))
            existing_consumer = _safe_consumer_id(existing.get("consumer_id"))

            if client_id is None:
                return None
            if existing_client != client_id:
                return None
            if (
                existing_consumer and
                existing_consumer != (consumer_id or client_id)
            ):
                return None

    if client_id is not None:
        leases[task_id] = {
            "client_id": client_id,
            "consumer_id": consumer_id or client_id,
            "leased_at": now,
            "lease_until": now + AI_LEASE_SECONDS,
        }
        save_state(state)

    return item


def acknowledge_ai(
    task_id: str,
    client_id: str | None = None,
    consumer_id: str | None = None,
) -> dict:
    client_id = _safe_client_id(client_id)
    consumer_id = _safe_consumer_id(consumer_id)
    state = load_state()

    lease = state.get("ai_delivery_leases", {}).get(task_id)
    if isinstance(lease, dict):
        lease_client = _safe_client_id(lease.get("client_id"))
        lease_consumer = _safe_consumer_id(lease.get("consumer_id"))

        if client_id != lease_client:
            return {
                "ok": False,
                "error": "AI work client mismatch",
                "reason": "AI_CLIENT_MISMATCH",
            }
        if lease_consumer and (consumer_id or client_id) != lease_consumer:
            return {
                "ok": False,
                "error": "AI work consumer mismatch",
                "reason": "AI_CONSUMER_MISMATCH",
            }

    result = _core_acknowledge_ai(task_id)

    if result.get("ok"):
        state = load_state()
        leases = state.setdefault("ai_delivery_leases", {})
        leases.pop(task_id, None)

        if not result.get("already_acked"):
            deliveries = state.setdefault("ai_deliveries", {})
            previous = deliveries.get(task_id)
            previous_attempts = (
                int(previous.get("attempts", 0))
                if isinstance(previous, dict)
                else 0
            )
            deliveries[task_id] = {
                "last_acked_at": time.time(),
                "attempts": previous_attempts + 1,
                "client_id": client_id,
            }

        save_state(state)

    return result


def _resolve_incident_after_ack(task_id: str) -> bool:
    """Persist ACK resolution in the incident record itself."""

    if not task_id.startswith("INCIDENT-"):
        return False

    incident_dir = (
        _WrapperPath.home()
        / ".local"
        / "state"
        / "prediction-research"
        / "incidents"
    )

    if not incident_dir.exists():
        return False

    for path in incident_dir.glob("*.json"):
        if _incident_outbox_id(path) != task_id:
            continue

        try:
            data = json.loads(
                path.read_text(encoding="utf-8")
            )
        except Exception:
            return False

        if data.get("status") == "OPEN":
            data["status"] = "RESOLVED"
            data["resolved_at"] = time.time()
            data["resolution"] = "BROWSER_ACK_RESOLVED"

            tmp = path.with_suffix(
                path.suffix + ".tmp"
            )

            tmp.write_text(
                json.dumps(
                    data,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            tmp.replace(path)

        return True

    return False


def acknowledge(
    task_id: str,
    client_id: str | None = None,
) -> dict:
    """ACK only from the chat client that owns the routed result."""

    client_id = _safe_client_id(client_id)
    state = load_state()
    route = _route_for_task(state, task_id)

    if route is not None and client_id != route:
        return {
            "ok": False,
            "error": "result client mismatch",
            "reason": "RESULT_CLIENT_MISMATCH",
        }

    result = _core_acknowledge(task_id)

    if not result.get("ok"):
        return result

    result["incident_resolved"] = (
        _resolve_incident_after_ack(task_id)
    )

    state = load_state()
    state.setdefault("result_delivery_leases", {}).pop(
        task_id,
        None,
    )

    if _queue_control_continue(
        state,
        task_id,
        "RESULT_ACKED",
    ):
        save_state(state)
    else:
        save_state(state)

    return result


def load_ai_response_receiver():
    path = ROOT / "control/hourly/ai_response_receiver.py"
    spec = importlib.util.spec_from_file_location(
        "prediction_research_ai_response_receiver",
        path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load AI response receiver from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        sys.modules.pop(spec.name, None)
        raise
    return mod


AI_RESPONSE_RECEIVER = load_ai_response_receiver()


class Handler(_CoreHandler):
    def client_id(self) -> str | None:
        return _safe_client_id(
            self.headers.get("X-Prediction-Client-Id", "")
        )

    def consumer_id(self) -> str | None:
        return _safe_consumer_id(
            self.headers.get("X-Prediction-Consumer-Id", "")
        )

    def do_GET(self):
        path = urlparse(self.path).path

        if path in {"/outbox", "/ai-outbox"}:
            if not self.authorized():
                self.send_json(401, {"error": "unauthorized"})
                return

            with LOCK:
                if path == "/outbox":
                    item = next_outbox_item(
                        self.client_id(),
                        self.consumer_id(),
                    )
                else:
                    item = next_ai_outbox_item(
                        self.client_id(),
                        self.consumer_id(),
                    )

            self.send_json(200, {"item": item})
            return

        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path

        if path == "/ai-response":
            if not self.authorized():
                self.send_json(401, {"error": "unauthorized"})
                return

            try:
                payload = self.read_json()
                with LOCK:
                    result = AI_RESPONSE_RECEIVER.receive(payload)
                self.send_json(200, result)
            except Exception as exc:
                detail = str(exc)
                exc_name = type(exc).__name__

                validation_error = (
                    isinstance(exc, AI_RESPONSE_RECEIVER.ResponseReceiverError)
                    or exc_name == "ValidationError"
                    or isinstance(exc, json.JSONDecodeError)
                )

                if "conflicting" in detail.lower():
                    status = 409
                elif validation_error:
                    status = 400
                else:
                    status = 500

                self.send_json(
                    status,
                    {
                        "error": exc_name,
                        "detail": detail,
                        "retryable": status >= 500,
                        "live_trading": False,
                        "paid_actions": False,
                        "wallet_actions": False,
                    },
                )
            return

        if path not in {"/enqueue", "/ack", "/ai-ack"}:
            return super().do_POST()

        if not self.authorized():
            self.send_json(401, {"error": "unauthorized"})
            return

        try:
            payload = self.read_json()

            if path == "/enqueue":
                envelope = BridgeEnvelope.model_validate(payload)
                result = enqueue(
                    envelope,
                    self.client_id(),
                )
                status = 200 if result.get("ok") else 409
            elif path == "/ack":
                task_id = str(payload.get("task_id", ""))
                with LOCK:
                    result = acknowledge(
                        task_id,
                        self.client_id(),
                    )
                status = 200 if result.get("ok") else 409
            else:
                task_id = str(payload.get("task_id", ""))
                with LOCK:
                    result = acknowledge_ai(
                        task_id,
                        self.client_id(),
                        self.consumer_id(),
                    )
                status = 200 if result.get("ok") else 409

            self.send_json(status, result)

        except Exception as exc:
            self.send_json(
                400,
                {
                    "error": type(exc).__name__,
                    "detail": str(exc),
                },
            )


def main():
    print(
        f"Prediction Research Browser Bridge listening "
        f"on http://{HOST}:{PORT}"
    )
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Bridge stopping.")


if __name__ == "__main__":
    main()
