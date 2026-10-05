from __future__ import annotations

import json
import time
import urllib.error
import urllib.request


def get_json(url: str):
    last_error = None
    for _ in range(20):
        try:
            with urllib.request.urlopen(url, timeout=4) as response:
                if response.status != 200:
                    raise RuntimeError(f"HTTP_{response.status}")
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as exc:
            last_error = exc
            time.sleep(0.5)
    raise RuntimeError(f"CONTROL_CENTER_NOT_READY:{last_error}")


def main() -> int:
    health = get_json("http://127.0.0.1:8770/api/health")
    if health.get("status") != "PASS" or not health.get("repo_exists"):
        raise RuntimeError("CONTROL_CENTER_HEALTH_INVALID")

    snapshot = get_json("http://127.0.0.1:8770/api/snapshot")
    if snapshot.get("schema") != "PREDICTION_CONTROL_CENTER_SNAPSHOT_V1":
        raise RuntimeError("CONTROL_CENTER_SCHEMA_INVALID")
    safety = snapshot.get("safety") or {}
    if any(safety.get(key) is not False for key in ("live_trading", "paid_actions", "wallet_actions")):
        raise RuntimeError("CONTROL_CENTER_SAFETY_INVALID")
    counts = snapshot.get("counts") or {}
    if int(counts.get("candidates") or 0) < 1:
        raise RuntimeError("CONTROL_CENTER_HISTORY_EMPTY")
    if not isinstance(snapshot.get("runs"), list):
        raise RuntimeError("CONTROL_CENTER_RUNS_MISSING")
    if not isinstance(snapshot.get("sessions"), list):
        raise RuntimeError("CONTROL_CENTER_SESSIONS_MISSING")
    print(
        "CONTROL_CENTER_CANARY_PASS "
        + json.dumps(
            {
                "candidates": counts.get("candidates"),
                "runs": counts.get("runs"),
                "tasks": counts.get("tasks"),
                "sessions": counts.get("sessions"),
                "legacy_candidates": counts.get("legacy_candidates"),
            },
            separators=(",", ":"),
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
