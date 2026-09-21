#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

root = Path.home() / "prediction_research_weather"
report = root / "evidence/weather/WEATHER-AWAY-A19B-latest.json"
v2 = root / "control/jobs/validate_madis_ldm_a19b_v2.py"

out = {
    "status": "DIAG",
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "root_exists": root.is_dir(),
    "report_exists": report.is_file(),
    "v2_validator_exists": v2.is_file(),
}

if root.is_dir():
    for key, cmd in {
        "branch": ["git", "branch", "--show-current"],
        "head": ["git", "rev-parse", "HEAD"],
        "tracked_status": ["git", "status", "--porcelain", "--untracked-files=no"],
    }.items():
        cp = subprocess.run(cmd, cwd=root, text=True, capture_output=True)
        out[key] = cp.stdout.strip()
        out[key + "_returncode"] = cp.returncode
        if cp.stderr.strip():
            out[key + "_stderr"] = cp.stderr.strip()[-4000:]

if report.is_file():
    try:
        out["report"] = json.loads(report.read_text(encoding="utf-8"))
    except Exception as exc:
        out["report_parse_error"] = f"{type(exc).__name__}: {exc}"

if v2.is_file():
    out["v2_validator_size"] = v2.stat().st_size

print(json.dumps(out, indent=2, sort_keys=True))
