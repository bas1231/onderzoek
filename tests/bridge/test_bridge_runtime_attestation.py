from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
CONTROL = ROOT / "control"
sys.path.insert(0, str(CONTROL))


def load_bridge():
    path = CONTROL / "browser_bridge.py"
    spec = importlib.util.spec_from_file_location(
        "prediction_test_browser_bridge_runtime_attestation",
        path,
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_commit_push_failure_is_not_durable_success():
    mod = load_bridge()
    original = mod._core_commit_and_push
    try:
        mod._core_commit_and_push = lambda message, stage_paths=None: (
            True,
            "committed locally; remote push failed: non-fast-forward",
        )
        ok, detail = mod.commit_and_push("x", [])
        assert ok is False
        assert "remote push failed" in detail
    finally:
        mod._core_commit_and_push = original


def test_stale_loaded_runtime_blocks_before_core_enqueue_and_schedules_reexec():
    mod = load_bridge()
    original_sync = mod._sync_main_fail_closed
    original_head = mod._current_head
    original_enqueue = mod._core_enqueue
    original_schedule = mod._schedule_bridge_reexec
    original_loaded = mod._LOADED_BRIDGE_COMMIT
    called = {"enqueue": 0, "reexec": 0}
    try:
        mod._LOADED_BRIDGE_COMMIT = "old-commit"
        mod._sync_main_fail_closed = lambda root: {"ok": True, "head": "new-commit"}
        mod._current_head = lambda: "new-commit"
        mod._core_enqueue = lambda envelope: called.__setitem__("enqueue", called["enqueue"] + 1)
        mod._schedule_bridge_reexec = lambda: called.__setitem__("reexec", called["reexec"] + 1)

        out = mod.enqueue(object())
        assert out["ok"] is False
        assert out["reason"] == "BRIDGE_RUNTIME_STALE_REEXEC_SCHEDULED"
        assert out["loaded_commit"] == "old-commit"
        assert out["current_head"] == "new-commit"
        assert out["recoverable"] is True
        assert called == {"enqueue": 0, "reexec": 1}
    finally:
        mod._sync_main_fail_closed = original_sync
        mod._current_head = original_head
        mod._core_enqueue = original_enqueue
        mod._schedule_bridge_reexec = original_schedule
        mod._LOADED_BRIDGE_COMMIT = original_loaded


def test_matching_runtime_delegates_only_after_successful_sync():
    mod = load_bridge()
    original_sync = mod._sync_main_fail_closed
    original_head = mod._current_head
    original_enqueue = mod._core_enqueue
    original_loaded = mod._LOADED_BRIDGE_COMMIT
    marker = object()
    try:
        mod._LOADED_BRIDGE_COMMIT = "same-commit"
        mod._sync_main_fail_closed = lambda root: {"ok": True, "head": "same-commit"}
        mod._current_head = lambda: "same-commit"
        mod._core_enqueue = lambda envelope: {"ok": True, "marker": envelope is marker}

        out = mod.enqueue(marker)
        assert out == {"ok": True, "marker": True}
    finally:
        mod._sync_main_fail_closed = original_sync
        mod._current_head = original_head
        mod._core_enqueue = original_enqueue
        mod._LOADED_BRIDGE_COMMIT = original_loaded


def test_sync_failure_blocks_without_enqueue_or_reexec():
    mod = load_bridge()
    original_sync = mod._sync_main_fail_closed
    original_enqueue = mod._core_enqueue
    original_schedule = mod._schedule_bridge_reexec
    called = {"enqueue": 0, "reexec": 0}
    try:
        mod._sync_main_fail_closed = lambda root: {
            "ok": False,
            "reason": "DIVERGED_HISTORY",
        }
        mod._core_enqueue = lambda envelope: called.__setitem__("enqueue", called["enqueue"] + 1)
        mod._schedule_bridge_reexec = lambda: called.__setitem__("reexec", called["reexec"] + 1)

        out = mod.enqueue(object())
        assert out["ok"] is False
        assert out["reason"] == "DIVERGED_HISTORY"
        assert called == {"enqueue": 0, "reexec": 0}
    finally:
        mod._sync_main_fail_closed = original_sync
        mod._core_enqueue = original_enqueue
        mod._schedule_bridge_reexec = original_schedule


if __name__ == "__main__":
    tests = [
        test_commit_push_failure_is_not_durable_success,
        test_stale_loaded_runtime_blocks_before_core_enqueue_and_schedules_reexec,
        test_matching_runtime_delegates_only_after_successful_sync,
        test_sync_failure_blocks_without_enqueue_or_reexec,
    ]
    for test in tests:
        test()
    print(f"BRIDGE_RUNTIME_ATTESTATION_TESTS_PASS {len(tests)}")
