from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("runtime_health", ROOT / "control/hourly/runtime_health.py")
health = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(health)

NOW = datetime(2026, 9, 24, 2, 30, tzinfo=timezone.utc)


def receipt(status: str, age_seconds: int = 0):
    return {
        "status": status,
        "timestamp_utc": (NOW - timedelta(seconds=age_seconds)).isoformat(),
    }


def test_missing_receipt_is_unverified_not_failure():
    result = health.classify(NOW, None, None)
    assert result["scheduler_runtime_state"] == "UNVERIFIED"
    assert not result["claims"]["scheduler_service_running"]


def test_recent_ready_is_preflight_not_running_claim():
    result = health.classify(NOW, receipt("READY", 60), {"status": "NO_CHANGES"})
    assert result["scheduler_runtime_state"] == "RECENT_PREFLIGHT"
    assert result["claims"]["scheduler_preflight_recent"] is True
    assert result["claims"]["scheduler_service_running"] is False
    assert result["claims"]["runtime_exchange_running"] is False


def test_old_ready_becomes_stale_idle():
    result = health.classify(NOW, receipt("READY", health.STALE_SECONDS + 1), None)
    assert result["scheduler_runtime_state"] == "STALE_IDLE"


def test_blocked_wins_while_receipt_is_fresh():
    result = health.classify(NOW, receipt("BLOCKED", 60), None)
    assert result["scheduler_runtime_state"] == "BLOCKED"


def test_malformed_timestamp_is_unverified():
    result = health.classify(NOW, {"status": "READY", "timestamp_utc": "bad"}, None)
    assert result["scheduler_runtime_state"] == "UNVERIFIED"
