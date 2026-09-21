#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys
import time

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "control"))

import executor as ex  # noqa: E402

TASK_ID = "WEATHER-AWAY-A19B-EXEC-001"
TASK = ROOT / "control" / "tasks" / "pending" / f"{TASK_ID}.json"
TARGET_REF = "ai/weather-madis-ldm-a19b"
MAX_WAIT_SECONDS = 4 * 60 * 60


def push_weather_branch() -> bool:
    result = ex.git("push", "origin", f"HEAD:{TARGET_REF}", check=False)
    if result.returncode == 0:
        print(f"Git push to {TARGET_REF}: PASS")
        return True
    print(f"Git push to {TARGET_REF}: FAILED")
    if result.stderr:
        print(result.stderr.strip())
    return False


ex.push_head_best_effort = push_weather_branch

if not TASK.exists():
    print(f"{TASK_ID}: pending task not found")
    raise SystemExit(2)
if not ex.task_is_committed(TASK):
    print(f"{TASK_ID}: task is not committed in HEAD")
    raise SystemExit(3)

started = time.time()
while TASK.exists() and time.time() - started < MAX_WAIT_SECONDS:
    outcome = ex.process_task(TASK)
    if outcome in {"completed", "failed", "blocked"}:
        raise SystemExit(0 if outcome == "completed" else 1)
    if outcome == "paused":
        time.sleep(30)
    elif outcome in {"awaiting_accept", "cadence_blocked"}:
        time.sleep(10)
    else:
        time.sleep(10)

print(f"{TASK_ID}: finite executor wait limit reached")
raise SystemExit(4)
