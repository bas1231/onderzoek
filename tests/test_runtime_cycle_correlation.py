from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("runtime_health", ROOT / "control/hourly/runtime_health.py")
health = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(health)


def test_recent_cycle_is_correlated_without_claiming_continuous_running():
    now = datetime(2026, 9, 24, 4, 0, tzinfo=timezone.utc)
    ts = (now - timedelta(minutes=1)).isoformat()
    sync = {"timestamp_utc": ts, "status": "READY"}
    checkpoint = {"status": "PUBLISHED", "head": "abc"}
    cycle = {
        "schema": "PVA_SCHEDULED_CYCLE_RECEIPT_V1",
        "timestamp_utc": ts,
        "run_id": "hourly-20260924T060000+0200",
        "status": "COMPLETED",
        "git_checkpoint_status": "PUBLISHED",
        "git_checkpoint_head": "abc",
    }
    result = health.classify(now, sync, checkpoint, cycle)
    assert result["scheduler_runtime_state"] == "RECENT_CYCLE_COMPLETED"
    assert result["scheduled_cycle"]["run_id"] == cycle["run_id"]
    assert result["claims"]["scheduled_cycle_recently_completed"] is True
    assert result["claims"]["scheduler_service_running"] is False
    assert result["claims"]["runtime_exchange_running"] is False


def test_stale_cycle_does_not_upgrade_fresh_preflight():
    now = datetime(2026, 9, 24, 4, 0, tzinfo=timezone.utc)
    sync = {"timestamp_utc": (now - timedelta(minutes=1)).isoformat(), "status": "READY"}
    cycle = {
        "schema": "PVA_SCHEDULED_CYCLE_RECEIPT_V1",
        "timestamp_utc": (now - timedelta(hours=2)).isoformat(),
        "run_id": "hourly-20260924T040000+0200",
        "status": "COMPLETED",
    }
    result = health.classify(now, sync, {"status": "NO_CHANGES"}, cycle)
    assert result["scheduler_runtime_state"] == "RECENT_PREFLIGHT"
    assert result["scheduled_cycle"]["recent"] is False


def test_malformed_cycle_fails_closed_to_preflight_only():
    now = datetime(2026, 9, 24, 4, 0, tzinfo=timezone.utc)
    sync = {"timestamp_utc": now.isoformat(), "status": "READY"}
    cycle = {"schema": "wrong", "timestamp_utc": now.isoformat(), "run_id": "hourly-x", "status": "COMPLETED"}
    result = health.classify(now, sync, None, cycle)
    assert result["scheduler_runtime_state"] == "RECENT_PREFLIGHT"
    assert result["scheduled_cycle"]["valid"] is False
