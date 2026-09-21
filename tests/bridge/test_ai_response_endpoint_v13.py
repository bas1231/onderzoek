from pathlib import Path
import importlib
import sys
from types import SimpleNamespace


def load_bridge():
    root = Path(__file__).resolve().parents[2]
    control = root / "control"
    if str(control) not in sys.path:
        sys.path.insert(0, str(control))
    sys.modules.pop("browser_bridge", None)
    sys.modules.pop("prediction_research_browser_bridge_core", None)
    return importlib.import_module("browser_bridge")


def handler_for(bb, sent):
    handler = object.__new__(bb.Handler)
    handler.path = "/ai-response"
    handler.authorized = lambda: True
    handler.read_json = lambda: {
        "run_id": "hourly-20260921T190000+0200",
        "response": {
            "run_id": "hourly-20260921T190000+0200"
        },
    }
    handler.send_json = lambda status, payload: sent.update({
        "status": status,
        "payload": payload,
    })
    return handler


def test_ai_response_endpoint_uses_dedicated_receiver(monkeypatch):
    bb = load_bridge()
    received = {}
    sent = {}
    error_type = bb.AI_RESPONSE_RECEIVER.ResponseReceiverError

    def receive(payload):
        received.update(payload)
        return {
            "ok": True,
            "run_id": payload["run_id"],
            "economic_conclusion": "NO_PROVEN_EDGE",
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
        }

    monkeypatch.setattr(
        bb,
        "AI_RESPONSE_RECEIVER",
        SimpleNamespace(
            receive=receive,
            ResponseReceiverError=error_type,
        ),
    )

    handler_for(bb, sent).do_POST()

    assert sent["status"] == 200
    assert sent["payload"]["ok"] is True
    assert received["run_id"] == "hourly-20260921T190000+0200"
    assert sent["payload"]["live_trading"] is False
    assert sent["payload"]["paid_actions"] is False
    assert sent["payload"]["wallet_actions"] is False


def test_validation_error_is_terminal_400(monkeypatch):
    bb = load_bridge()
    sent = {}
    error_type = bb.AI_RESPONSE_RECEIVER.ResponseReceiverError

    def receive(_payload):
        raise error_type("AI response_token mismatch")

    monkeypatch.setattr(
        bb,
        "AI_RESPONSE_RECEIVER",
        SimpleNamespace(
            receive=receive,
            ResponseReceiverError=error_type,
        ),
    )

    handler_for(bb, sent).do_POST()
    assert sent["status"] == 400
    assert sent["payload"]["retryable"] is False


def test_internal_error_is_retryable_500(monkeypatch):
    bb = load_bridge()
    sent = {}
    error_type = bb.AI_RESPONSE_RECEIVER.ResponseReceiverError

    def receive(_payload):
        raise RuntimeError("synthetic orchestration crash")

    monkeypatch.setattr(
        bb,
        "AI_RESPONSE_RECEIVER",
        SimpleNamespace(
            receive=receive,
            ResponseReceiverError=error_type,
        ),
    )

    handler_for(bb, sent).do_POST()
    assert sent["status"] == 500
    assert sent["payload"]["retryable"] is True


def test_browser_bridge_core_is_preserved():
    bb = load_bridge()
    assert hasattr(bb, "enqueue")
    assert hasattr(bb, "next_outbox_item")
    assert hasattr(bb, "next_ai_outbox_item")
    assert issubclass(bb.Handler, bb._CoreHandler)
