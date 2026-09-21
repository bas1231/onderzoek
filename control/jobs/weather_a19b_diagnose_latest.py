#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

root = Path.home() / "prediction_research_weather"
report = root / "evidence/weather/WEATHER-AWAY-A19B-latest.json"

out = {
    "task": "WEATHER-A19B-DIAGNOSE-LATEST",
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
}

if root.is_dir():
    for key, cmd in {
        "branch": ["git", "branch", "--show-current"],
        "head": ["git", "rev-parse", "HEAD"],
        "status": ["git", "status", "--porcelain"],
    }.items():
        cp = subprocess.run(cmd, cwd=root, text=True, capture_output=True, timeout=30)
        out[key] = {
            "returncode": cp.returncode,
            "stdout": cp.stdout[-8000:].strip(),
            "stderr": cp.stderr[-4000:].strip(),
        }
else:
    out["worktree"] = "MISSING"

if report.is_file():
    try:
        obj = json.loads(report.read_text(encoding="utf-8"))
        out["report"] = obj
    except Exception as exc:
        out["report_error"] = f"{type(exc).__name__}: {exc}"
else:
    out["report"] = "MISSING"

print(json.dumps(out, indent=2, sort_keys=True))
