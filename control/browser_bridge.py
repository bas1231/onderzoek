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
