from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path.home() / ".local/state/prediction-research"
SYNC = STATE / "prod-runtime-sync-latest.json"
CHECKPOINT = STATE / "git-checkpoint-latest.json"
HEALTH = STATE / "runtime-health-latest.json"

# Hourly timer + AccuracySec=30s. 90 minutes separates a missed/blocked cycle
# from normal scheduling jitter without calling a quiet exchange a failure.
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


def classify(now: datetime, sync: dict[str, Any] | None, checkpoint: dict[str, Any] | None) -> dict[str, Any]:
    now = now.astimezone(timezone.utc)
    sync_ts = parse_ts((sync or {}).get("timestamp_utc"))
    age = None if sync_ts is None else max(0, int((now - sync_ts).total_seconds()))
    sync_status = (sync or {}).get("status")
    checkpoint_status = (checkpoint or {}).get("status")

    if sync is None or sync_ts is None:
        state = "UNVERIFIED"
        reason = "no valid runtime-sync receipt"
    elif sync_status == "BLOCKED":
        state = "BLOCKED"
        reason = "latest runtime-sync receipt is fail-closed BLOCKED"
    elif age is not None and age > STALE_SECONDS:
        state = "STALE_IDLE"
        reason = "latest runtime-sync receipt is older than hourly liveness window"
    elif sync_status == "READY":
        # READY proves a recent scheduler preflight executed. It does not prove
        # browser, bridge, exchange polling, or a completed research cycle.
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
        "claims": {
            "scheduler_preflight_recent": state == "RECENT_PREFLIGHT",
            "scheduler_service_running": False,
            "browser_bridge_running": False,
            "runtime_exchange_running": False,
        },
        "interpretation": {
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
    result = classify(datetime.now(timezone.utc), read_json(SYNC), read_json(CHECKPOINT))
    HEALTH.parent.mkdir(parents=True, exist_ok=True)
    HEALTH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2 if result["scheduler_runtime_state"] == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
