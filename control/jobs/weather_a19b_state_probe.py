#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

ROOT = Path.home() / "prediction_research_weather"
REPORT = ROOT / "evidence/weather/WEATHER-AWAY-A19B-latest.json"
V1 = ROOT / "control/jobs/validate_madis_ldm_a19b.py"
V2 = ROOT / "control/jobs/validate_madis_ldm_a19b_v2.py"


def sh(*args: str) -> dict:
    cp = subprocess.run(args, cwd=ROOT if ROOT.is_dir() else None, text=True, capture_output=True, timeout=30)
    return {"returncode": cp.returncode, "stdout": cp.stdout[-12000:], "stderr": cp.stderr[-6000:]}

out = {
    "task": "WEATHER-A19B-STATE-PROBE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "economic_conclusion": "NO_PROVEN_EDGE",
    "root_exists": ROOT.is_dir(),
}

if ROOT.is_dir():
    out["branch"] = sh("git", "branch", "--show-current")
    out["head"] = sh("git", "rev-parse", "HEAD")
    out["status"] = sh("git", "status", "--porcelain")
    out["v1_validator_exists"] = V1.is_file()
    out["v2_validator_exists"] = V2.is_file()
    out["report_exists"] = REPORT.is_file()
    if REPORT.is_file():
        try:
            out["report"] = json.loads(REPORT.read_text(encoding="utf-8"))
        except Exception as exc:
            out["report_parse_error"] = f"{type(exc).__name__}: {exc}"

print(json.dumps(out, indent=2, sort_keys=True))
