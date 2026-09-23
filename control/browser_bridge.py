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
_core_next_ai_outbox_item = next_ai_outbox_item
_core_acknowledge_ai = acknowledge_ai
_core_acknowledge = acknowledge
_core_enqueue = enqueue
_core_commit_and_push = commit_and_push

from executor_preflight import sync_main_fail_closed as _sync_main_fail_closed


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


def enqueue(envelope):
    """Synchronize and attest the bridge runtime before accepting a task."""
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

        return _core_enqueue(envelope)

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


def next_ai_outbox_item():
    state = load_state()
    retry = _stalled_ai_retry(state)
    if retry is not None:
        return retry
    return _core_next_ai_outbox_item()


def acknowledge_ai(task_id: str) -> dict:
    result = _core_acknowledge_ai(task_id)

    if result.get("ok") and not result.get("already_acked"):
        state = load_state()
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
        }
        save_state(state)

    return result


def _incident_outbox_id(path: _WrapperPath) -> str:
    raw = "INCIDENT-" + path.stem

    return "".join(
        ch
        if ch.isalnum() or ch in "._:-"
        else "_"
        for ch in raw
    )[:150]


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


def acknowledge(task_id: str) -> dict:
    """ACK the result and durably close incident-backed outbox items."""

    result = _core_acknowledge(task_id)

    if not result.get("ok"):
        return result

    result["incident_resolved"] = (
        _resolve_incident_after_ack(task_id)
    )

    state = load_state()

    if _queue_control_continue(
        state,
        task_id,
        "RESULT_ACKED",
    ):
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
    def do_POST(self):
        path = urlparse(self.path).path

        if path != "/ai-response":
            return super().do_POST()

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
