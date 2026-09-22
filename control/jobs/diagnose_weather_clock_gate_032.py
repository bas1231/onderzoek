#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path.cwd()
TASK_ID = "WEATHER-NIST-CLOCK-GATE-032"

candidates = [
    ROOT / "control" / "results" / TASK_ID / "RESULT.json",
    ROOT / "control" / "tasks" / "completed" / f"{TASK_ID}.json",
    ROOT / "control" / "tasks" / "failed" / f"{TASK_ID}.json",
    ROOT / "control" / "tasks" / "running" / f"{TASK_ID}.json",
    ROOT / "control" / "tasks" / "pending" / f"{TASK_ID}.json",
]

out = {
    "task_id": TASK_ID,
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "files": {},
    "weather_clock_candidates": [],
}

for path in candidates:
    if path.exists():
        try:
            text = path.read_text(encoding="utf-8")
            out["files"][str(path)] = json.loads(text)
        except Exception as exc:
            out["files"][str(path)] = {
                "read_error": f"{type(exc).__name__}: {exc}"
            }

for base in [ROOT / "control" / "jobs", ROOT / "control" / "weather", ROOT / "evidence" / "weather"]:
    if base.exists():
        for path in sorted(base.glob("*clock*")) + sorted(base.glob("*nist*")):
            if path.is_file():
                out["weather_clock_candidates"].append(str(path.relative_to(ROOT)))

out["status"] = "PASS_DIAGNOSTIC" if out["files"] else "BLOCKED_RESULT_NOT_FOUND"
print(json.dumps(out, indent=2, sort_keys=True))
raise SystemExit(0 if out["files"] else 2)
