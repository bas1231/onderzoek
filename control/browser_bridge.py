# Thin V13 wrapper around the preserved browser bridge implementation.
# The original implementation is stored byte-for-byte in browser_bridge_core.py.
# Executing it in this module's globals preserves monkeypatch/test semantics while
# letting the AI-response channel stay separate from the generic executor route.

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
    forbidden = {
        "command",
        "shell",
        "argv",
        "exec",
        "executable",
    }
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

        # This check suppresses retry as soon as either a final response or a
        # durable response receipt exists for the correlated run.
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

    # Do not refresh the timeout for duplicate browser ACK retries. A real
    # initial delivery or a deliberate stale-bundle retry goes through the
    # normal success path without already_acked=True.
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

            # Client/AI validation failures are terminal for that exact
            # response block. Unexpected runtime failures are retryable so
            # the browser capture does not permanently discard valid work.
            validation_error = (
                isinstance(
                    exc,
                    AI_RESPONSE_RECEIVER.ResponseReceiverError,
                )
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
    server = ThreadingHTTPServer(
        (HOST, PORT),
        Handler,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Bridge stopping.")


if __name__ == "__main__":
    main()
