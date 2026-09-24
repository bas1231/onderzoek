from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path.home() / ".local/state/prediction-research"
SYNC = STATE / "prod-runtime-sync-latest.json"
CHECKPOINT = STATE / "git-checkpoint-latest.json"
CYCLE = STATE / "scheduled-cycle-latest.json"
HEALTH = STATE / "runtime-health-latest.json"
STALE_SECONDS = 90 * 60


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def classify(now: datetime, sync: dict[str, Any] | None, checkpoint: dict[str, Any] | None, cycle: dict[str, Any] | None = None) -> dict[str, Any]:
    now = now.astimezone(timezone.utc)
    sync_ts = parse_ts((sync or {}).get("timestamp_utc"))
    age = None if sync_ts is None else max(0, int((now - sync_ts).total_seconds()))
    sync_status = (sync or {}).get("status")
    checkpoint_status = (checkpoint or {}).get("status")

    cycle_valid = bool(
        cycle
        and cycle.get("schema") == "PVA_SCHEDULED_CYCLE_RECEIPT_V1"
        and cycle.get("status") == "COMPLETED"
        and isinstance(cycle.get("run_id"), str)
        and cycle.get("run_id", "").startswith("hourly-")
        and parse_ts(cycle.get("timestamp_utc")) is not None
    )
    cycle_ts = parse_ts((cycle or {}).get("timestamp_utc")) if cycle_valid else None
    cycle_age = None if cycle_ts is None else max(0, int((now - cycle_ts).total_seconds()))
    cycle_recent = bool(cycle_valid and cycle_age is not None and cycle_age <= STALE_SECONDS)

    if sync is None or sync_ts is None:
        state = "UNVERIFIED"
        reason = "no valid runtime-sync receipt"
    elif sync_status == "BLOCKED":
        state = "BLOCKED"
        reason = "latest runtime-sync receipt is fail-closed BLOCKED"
    elif age is not None and age > STALE_SECONDS:
        state = "STALE_IDLE"
        reason = "latest runtime-sync receipt is older than hourly liveness window"
    elif sync_status == "READY" and cycle_recent:
        state = "RECENT_CYCLE_COMPLETED"
        reason = "recent preflight plus correlated completed scheduled-cycle receipt observed"
    elif sync_status == "READY":
        state = "RECENT_PREFLIGHT"
        reason = "recent runtime-sync READY receipt observed"
    else:
        state = "UNVERIFIED"
        reason = f"unrecognized runtime-sync status: {sync_status!r}"

    return {
        "schema": "PVA_RUNTIME_HEALTH_V1",
        "timestamp_utc": now.isoformat(),
        "scheduler_runtime_state": state,
        "reason": reason,
        "runtime_sync_status": sync_status,
        "runtime_sync_age_seconds": age,
        "git_checkpoint_status": checkpoint_status,
        "scheduled_cycle": {
            "valid": cycle_valid,
            "recent": cycle_recent,
            "age_seconds": cycle_age,
            "run_id": (cycle or {}).get("run_id") if cycle_valid else None,
            "git_checkpoint_status": (cycle or {}).get("git_checkpoint_status") if cycle_valid else None,
            "git_checkpoint_head": (cycle or {}).get("git_checkpoint_head") if cycle_valid else None,
        },
        "claims": {
            "scheduler_preflight_recent": state in {"RECENT_PREFLIGHT", "RECENT_CYCLE_COMPLETED"},
            "scheduled_cycle_recently_completed": state == "RECENT_CYCLE_COMPLETED",
            "scheduler_service_running": False,
            "browser_bridge_running": False,
            "runtime_exchange_running": False,
        },
        "interpretation": {
            "RECENT_CYCLE_COMPLETED": "fresh local preflight and completed wrapper receipt; not a continuous UP/RUNNING attestation",
            "RECENT_PREFLIGHT": "fresh local preflight evidence only; not an UP/RUNNING attestation",
            "STALE_IDLE": "no recent preflight receipt; may be idle/offline/blocked outside observable state",
            "BLOCKED": "latest preflight failed closed",
            "UNVERIFIED": "insufficient valid local receipt evidence",
        },
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "openai_api": False,
    }


def main() -> int:
    result = classify(
        datetime.now(timezone.utc),
        read_json(SYNC),
        read_json(CHECKPOINT),
        read_json(CYCLE),
    )
    HEALTH.parent.mkdir(parents=True, exist_ok=True)
    tmp = HEALTH.with_suffix(".tmp")
    tmp.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(HEALTH)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2 if result["scheduler_runtime_state"] == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
