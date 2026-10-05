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


def get_text(url: str):
    last_error = None
    for _ in range(20):
        try:
            with urllib.request.urlopen(url, timeout=4) as response:
                if response.status != 200:
                    raise RuntimeError(f"HTTP_{response.status}")
                return response.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as exc:
            last_error = exc
            time.sleep(0.5)
    raise RuntimeError(f"CONTROL_CENTER_UI_NOT_READY:{last_error}")


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
    if not isinstance(snapshot.get("chain_alerts"), list):
        raise RuntimeError("CONTROL_CENTER_CHAIN_ALERTS_MISSING")
    build_log = snapshot.get("build_log")
    if not isinstance(build_log, dict):
        raise RuntimeError("CONTROL_CENTER_BUILD_LOG_MISSING")
    if not isinstance(build_log.get("open_work"), list) or not isinstance(build_log.get("recent_events"), list):
        raise RuntimeError("CONTROL_CENTER_BUILD_LOG_INVALID")
    if "sync_request" not in snapshot:
        raise RuntimeError("CONTROL_CENTER_SYNC_REQUEST_STATE_MISSING")
    lifecycle = snapshot.get("lifecycle")
    if not isinstance(lifecycle, dict):
        raise RuntimeError("CONTROL_CENTER_LIFECYCLE_MISSING")
    if lifecycle.get("full_chain_status") != "NOT_PROVEN":
        raise RuntimeError("CONTROL_CENTER_LIFECYCLE_OVERCLAIM")
    stages = lifecycle.get("stages")
    if not isinstance(stages, list) or len(stages) != 9:
        raise RuntimeError("CONTROL_CENTER_LIFECYCLE_STAGES_INVALID")
    if lifecycle.get("invariant") != "NO_TEST_OR_MEASUREMENT_BEFORE_ASTRA_POSTBUILD_APPROVAL":
        raise RuntimeError("CONTROL_CENTER_LIFECYCLE_INVARIANT_INVALID")

    sync = snapshot.get("git_sync")
    if not isinstance(sync, dict) or sync.get("status") not in {"GREEN", "AMBER", "RED", "UNKNOWN"}:
        raise RuntimeError("CONTROL_CENTER_GIT_SYNC_MISSING")
    html = get_text("http://127.0.0.1:8770/")
    for needle in ("Logboek", "Sync gestart…", "/api/sync", "fail-closed reconciliatie", "Actieve systeemacties", "Git-sync productie → main", "nieuwe Prediction ChatGPT-sessie", "opent altijd een nieuwe Prediction ChatGPT-sessie"):
        if needle not in html:
            raise RuntimeError("CONTROL_CENTER_SYNC_UI_MISSING:" + needle)
    active_states = {
        "RUNNING", "STARTED", "CLAIMED", "INFLIGHT",
        "CONTINUE_QUEUED", "PENDING",
    }
    tasks = snapshot.get("tasks")
    if not isinstance(tasks, list):
        raise RuntimeError("CONTROL_CENTER_TASKS_MISSING")
    if int(counts.get("tasks") or 0) != len(tasks):
        raise RuntimeError("CONTROL_CENTER_ACTIVE_TASK_COUNT_MISMATCH")
    if any(str(item.get("status") or "").upper() not in active_states for item in tasks):
        raise RuntimeError("CONTROL_CENTER_HISTORICAL_TASK_EXPOSED")
    print(
        "CONTROL_CENTER_CANARY_PASS "
        + json.dumps(
            {
                "candidates": counts.get("candidates"),
                "runs": counts.get("runs"),
                "tasks": counts.get("tasks"),
                "sessions": counts.get("sessions"),
                "legacy_candidates": counts.get("legacy_candidates"),
                "chain_alerts": len(snapshot.get("chain_alerts") or []),
                "git_sync": (snapshot.get("git_sync") or {}).get("status"),
                "lifecycle": (snapshot.get("lifecycle") or {}).get("full_chain_status"),
                "build_log_items": (snapshot.get("build_log") or {}).get("counts", {}).get("work_items"),
                "sync_request_state": (snapshot.get("sync_request") or {}).get("state"),
            },
            separators=(",", ":"),
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
