from pathlib import Path
import importlib.util
import sys


def load_poller():
    root = Path(__file__).resolve().parents[2]
    path = root / "control" / "bridge_commands" / "command_bus_poller.py"
    spec = importlib.util.spec_from_file_location("command_bus_poller_continuation_test", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def base_command():
    return {
        "schema": "PREDICTION_BRIDGE_COMMAND_V1",
        "task_id": "CONTINUATION-META-TEST-001",
        "action": "BRIDGE_PING",
        "created_at_utc": "2026-10-02T12:00:00Z",
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "intelligence_tier": "C",
        "issuer": {
            "model": "GPT-5.6 Sol",
            "reasoning_level": "UNAVAILABLE_TO_RUNTIME",
        },
    }


def test_auto_continue_and_parent_lineage_validate():
    mod = load_poller()
    command = base_command()
    command["auto_continue"] = True
    command["parent_continuation_id"] = "CONT-" + ("a" * 24)
    ok, reason = mod.validate_command(command)
    assert ok is True
    assert reason == "OK"


def test_bad_parent_lineage_is_rejected():
    mod = load_poller()
    command = base_command()
    command["parent_continuation_id"] = "not-a-continuation"
    ok, reason = mod.validate_command(command)
    assert ok is False
    assert reason == "BAD_PARENT_CONTINUATION_ID"


def test_headless_auto_continue_is_rejected():
    mod = load_poller()
    command = base_command()
    command["delivery_mode"] = "headless"
    command["auto_continue"] = True
    ok, reason = mod.validate_command(command)
    assert ok is False
    assert reason == "HEADLESS_AUTO_CONTINUE_FORBIDDEN"


def test_headless_terminal_receipt_with_parent_is_allowed():
    mod = load_poller()
    command = base_command()
    command["delivery_mode"] = "headless"
    command["auto_continue"] = False
    command["parent_continuation_id"] = "CONT-" + ("b" * 24)
    ok, reason = mod.validate_command(command)
    assert ok is True
    assert reason == "OK"
