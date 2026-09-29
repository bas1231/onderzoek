#!/usr/bin/env python3
"""Deterministic offline tests for the Prediction command bus components."""

from __future__ import annotations

import importlib.util
import py_compile
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_poller_validation() -> None:
    poller = load("command_bus_poller_test", HERE / "command_bus_poller.py")
    valid = {
        "schema": "PREDICTION_BRIDGE_COMMAND_V1",
        "task_id": "SELFTEST-E001",
        "action": "BRIDGE_PING",
        "created_at_utc": "2026-09-29T10:00:00Z",
        "route_task_id": None,
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "intelligence_tier": "C",
        "issuer": {"model": "deterministic-selftest", "reasoning_level": "none"},
    }
    assert poller.validate_command(valid) == (True, "OK")
    for field, code in [
        ("live_trading", "LIVE_TRADING_BLOCKED"),
        ("paid_actions", "PAID_ACTIONS_BLOCKED"),
        ("wallet_actions", "WALLET_ACTIONS_BLOCKED"),
    ]:
        bad = dict(valid)
        bad[field] = True
        assert poller.validate_command(bad) == (False, code)
    bad = dict(valid)
    bad["unknown"] = 1
    assert poller.validate_command(bad) == (False, "UNKNOWN_FIELDS")


def test_inflight_patch() -> None:
    patcher = load("patch_wake_inflight_test", HERE / "patch_wake_inflight.py")
    fixture = '''#!/usr/bin/env python3
import os
import time
from pathlib import Path
DATA_DIR = Path("/tmp/x")
OUTBOX = DATA_DIR / "outbox"
SENT = DATA_DIR / "sent"
ROUTES = DATA_DIR / "routes"
def ensure_dirs():
    for p in (OUTBOX, SENT, ROUTES):
        p.mkdir(parents=True, exist_ok=True)
def oldest_event(chat_id, consumer_id):
    return None, None
class H:
    def reply_json(self, status, obj): pass
    def demo(self, chat_id, consumer_id, event_id):
        deadline = time.monotonic() + 20.0
        while time.monotonic() < deadline:
            _, obj = oldest_event(chat_id, consumer_id)
            if obj is not None:
                self.reply_json(200, obj)
                return
            time.sleep(0.25)
        src = OUTBOX / f"{event_id}.json"
        dst = SENT / f"{event_id}.json"
        if src.exists():
            pass
        health = {
                "consumer_routing": True,
        }
'''
    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / "bridge_server.py"
        target.write_text(fixture, encoding="utf-8")
        patcher.patch(target)
        text = target.read_text(encoding="utf-8")
        assert patcher.MARKER in text
        assert 'INFLIGHT = DATA_DIR / "inflight"' in text
        assert "os.replace(path, claimed)" in text
        assert "inflight_src if inflight_src.exists() else outbox_src" in text
        py_compile.compile(str(target), doraise=True)


def main() -> int:
    for path in (HERE / "command_bus_poller.py", HERE / "patch_wake_inflight.py", HERE / "install_command_bus.py"):
        py_compile.compile(str(path), doraise=True)
    test_poller_validation()
    test_inflight_patch()
    print("PASS: command bus deterministic self-tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
