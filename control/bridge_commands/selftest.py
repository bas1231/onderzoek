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


BASE_FIXTURE = '''#!/usr/bin/env python3
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
class Handler:
    def reply_json(self, status, obj): pass
    def authorized(self): return True
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


def assert_patched(patcher, target: Path) -> None:
    text = target.read_text(encoding="utf-8")
    assert patcher.MARKER in text
    assert 'INFLIGHT = DATA_DIR / "inflight"' in text
    assert "os.replace(path, claimed)" in text
    assert "inflight_src if inflight_src.exists() else outbox_src" in text
    assert patcher.static_inflight_ok(target)
    py_compile.compile(str(target), doraise=True)


def test_inflight_patch_direct_base() -> None:
    patcher = load("patch_wake_inflight_direct_test", HERE / "patch_wake_inflight.py")
    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / "bridge_server.py"
        target.write_text(BASE_FIXTURE, encoding="utf-8")
        actual, _, kind = patcher.patch(target)
        assert actual == target
        assert kind == "direct_base"
        assert_patched(patcher, target)


def test_inflight_patch_hardened_wrapper() -> None:
    patcher = load("patch_wake_inflight_wrapper_test", HERE / "patch_wake_inflight.py")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        base = root / "bridge_server_v2.py"
        wrapper = root / "bridge_server.py"
        base.write_text(BASE_FIXTURE, encoding="utf-8")
        wrapper_source = '''#!/usr/bin/env python3
import bridge_server_v2 as base
class Handler(base.Handler):
    server_version = "PredictionChatWake/0.8-hardened"
'''
        wrapper.write_text(wrapper_source, encoding="utf-8")
        before = wrapper.read_bytes()
        actual, _, kind = patcher.patch(wrapper)
        assert actual == base
        assert kind == "hardened_wrapper"
        assert wrapper.read_bytes() == before, "wrapper must remain untouched"
        assert_patched(patcher, base)
        py_compile.compile(str(wrapper), doraise=True)


def test_inflight_idempotent() -> None:
    patcher = load("patch_wake_inflight_idempotent_test", HERE / "patch_wake_inflight.py")
    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / "bridge_server.py"
        target.write_text(BASE_FIXTURE, encoding="utf-8")
        patcher.patch(target)
        first = target.read_bytes()
        _, backup, _ = patcher.patch(target)
        assert backup is None
        assert target.read_bytes() == first


def main() -> int:
    for path in (
        HERE / "command_bus_poller.py",
        HERE / "patch_wake_inflight.py",
        HERE / "install_command_bus.py",
    ):
        py_compile.compile(str(path), doraise=True)
    test_poller_validation()
    test_inflight_patch_direct_base()
    test_inflight_patch_hardened_wrapper()
    test_inflight_idempotent()
    print("PASS: command bus deterministic self-tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
