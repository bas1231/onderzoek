"""Read-only readiness check for a later, separately gated recovery launch canary.

No claim, launch token, wake event, routing write, service mutation, browser
action or paid activity is possible in this preflight.
"""
from __future__ import annotations

import json
from pathlib import Path
import time

try:
    from control.independent_continuity.coordinator import (
        UnsafeLaunch, read_safe, fresh_launcher, verify_source_fresh,
    )
except ModuleNotFoundError:
    from coordinator import UnsafeLaunch, read_safe, fresh_launcher, verify_source_fresh


def assess(home: Path, *, now_unix: float) -> dict:
    scope_file = home / ".local/state/prediction-project-executor/independent-continuity/scope.json"
    config = read_safe(scope_file)
    if config.get("schema") != "PREDICTION_INDEPENDENT_CONTINUITY_SCOPE_V1":
        raise UnsafeLaunch("BAD_OBSERVATION_SCOPE_SCHEMA")
    if config.get("mode") != "observe":
        raise UnsafeLaunch("PREFLIGHT_REQUIRES_OBSERVE_MODE")
    if any(config.get(key) is not False for key in
           ("live_trading", "paid_actions", "wallet_actions")):
        raise UnsafeLaunch("PREFLIGHT_UNSAFE_SCOPE_FLAGS")
    allowed = config.get("work_item_ids")
    if not isinstance(allowed, list) or not allowed or not all(
            isinstance(item, str) and item for item in allowed):
        raise UnsafeLaunch("PREFLIGHT_MISSING_EXPLICIT_SCOPE")
    fetched = home / ".local/share/prediction-command-bus/repo/.git/FETCH_HEAD"
    verify_source_fresh(fetched, now_unix=now_unix, max_age=180)
    launcher = fresh_launcher(
        home / ".local/share/prediction-chat-bridge", now_unix=now_unix
    )
    if launcher.get("schema") != "PREDICTION_DASHBOARD_LAUNCHER_V1":
        raise UnsafeLaunch("PREFLIGHT_UNEXPECTED_LAUNCHER")
    # Intentionally do not return chat ID, consumer ID or task identifiers.
    return {
        "status": "READY_READ_ONLY",
        "mode": "observe",
        "latest_proven_browser_launcher": True,
        "fetched_source_fresh": True,
        "write_events": 0,
        "new_chat_launched": False,
        "auto_continue_enabled": False,
    }


def main() -> int:
    try:
        result = assess(Path.home(), now_unix=time.time())
    except (UnsafeLaunch, OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        reason = str(exc).replace("\n", " ")[:170]
        print("CONTINUITY_PREFLIGHT_BLOCKED=" + reason, flush=True)
        return 2
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
