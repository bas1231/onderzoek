"""Independent continuity periodic runner; only own state and existing event protocol.

The default mode is 'observe'. Even when enabled, launch requires a fresh
authenticated dashboard browser registration and explicit scoped work items.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

try:
    from control.independent_continuity.observer import scan
    from control.independent_continuity.coordinator import process_once, UnsafeLaunch
except ModuleNotFoundError:
    from observer import scan
    from coordinator import process_once, UnsafeLaunch


def run(config: dict, *, home: Path, now_unix: float) -> dict:
    if config.get("schema") != "PREDICTION_INDEPENDENT_CONTINUITY_SCOPE_V1":
        raise UnsafeLaunch("unknown runner config schema")
    mode = config.get("mode")
    if mode not in {"disabled", "observe", "emit"}:
        raise UnsafeLaunch("unknown mode")
    if mode == "disabled":
        return {"status": "DISABLED", "bridge_mutated": False}
    allow = config.get("work_item_ids")
    if (not isinstance(allow, list) or not allow or
            any(not isinstance(x, str) or not x or len(x) > 160 for x in allow)):
        raise UnsafeLaunch("explicit work item list required")
    stale_minutes = config.get("stale_minutes", 90)
    if type(stale_minutes) is not int or stale_minutes < 30:
        raise UnsafeLaunch("invalid stale minutes")
    if config.get("live_trading") is not False or config.get("paid_actions") is not False or config.get("wallet_actions") is not False:
        raise UnsafeLaunch("safety flags must be false")
    # Paths are intentionally hardcoded to well-documented existing snapshots.
    repo = home / ".local/share/prediction-command-bus/repo"
    bridge = home / ".local/share/prediction-chat-bridge"
    state = home / ".local/state/prediction-project-executor/independent-continuity"
    source = repo / "control/build_log/events"
    fetch_head = repo / ".git/FETCH_HEAD"
    if source.is_symlink() or state.is_symlink():
        raise UnsafeLaunch("symlink source/state refused")
    # Freshness checked BEFORE recording observations, so stale mirrors never
    # appear to be an authoritative source of current build activity.
    from_coordinator = None
    try:
        from control.independent_continuity.coordinator import verify_source_fresh
        from_coordinator = verify_source_fresh
    except ModuleNotFoundError:
        from coordinator import verify_source_fresh
        from_coordinator = verify_source_fresh
    from_coordinator(fetch_head, now_unix=now_unix, max_age=180)
    proposals = state / "proposals"
    snapshot = scan(source, proposals, datetime.fromtimestamp(now_unix, timezone.utc), stale_minutes)
    if snapshot["status"] != "PASS":
        raise UnsafeLaunch("invalid event snapshot")
    if mode == "observe":
        result = {"state": "OBSERVATION_ONLY", "emitted": False,
                  "note": "No browser dependency or wake-bridge write in observe mode."}
    else:
        result = process_once(
            source, proposals, state, bridge, fetch_head, set(allow),
            now_unix=now_unix, emit=True, stale_minutes=stale_minutes
        )
    return {
        "status": "PASS",
        "mode": mode,
        "observed_build_events": snapshot["observed_events"],
        "stale_observations": len(snapshot["observations"]),
        "fresh_proposals": len(snapshot["new_report_files"]),
        "coordinator": result,
        "bridge_mutated": bool(result.get("emitted")),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.config.is_symlink() or not args.config.is_file():
            raise UnsafeLaunch("configuration missing or symlink")
        config = json.loads(args.config.read_text(encoding="utf-8"))
        result = run(config, home=args.home, now_unix=time.time())
        print(json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
        return 0
    except (ValueError, OSError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "reason": str(exc)}), flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
