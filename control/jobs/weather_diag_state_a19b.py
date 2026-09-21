#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

ROOT = Path.home() / "prediction_research_weather"
REPORT = ROOT / "evidence/weather/WEATHER-AWAY-A19B-latest.json"
V2_FILES = [
    ROOT / "control/weather/madis_ldm_queue_reader_a19b_v2.c",
    ROOT / "control/weather/madis_ldm_queue_ingest_a19b_v2.py",
    ROOT / "control/weather/test_madis_ldm_queue_a19b_v2.py",
    ROOT / "control/weather/test_madis_ldm_queue_a19b_v2_adversarial.py",
    ROOT / "control/jobs/validate_madis_ldm_a19b_v2.py",
]


def run(*args: str) -> dict:
    cp = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=30)
    return {
        "returncode": cp.returncode,
        "stdout": cp.stdout[-12000:],
        "stderr": cp.stderr[-6000:],
    }

out = {
    "status": "DIAGNOSTIC_ONLY",
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
}

if not ROOT.is_dir():
    out["reason"] = "WEATHER_WORKTREE_MISSING"
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(2)

out["branch"] = run("git", "branch", "--show-current")
out["head"] = run("git", "rev-parse", "HEAD")
out["status_porcelain"] = run("git", "status", "--porcelain")
out["last_commits"] = run("git", "log", "-8", "--oneline", "--decorate")
out["v2_files"] = {str(p.relative_to(ROOT)): p.exists() for p in V2_FILES}

if REPORT.is_file():
    try:
        out["a19b_v1_report"] = json.loads(REPORT.read_text(encoding="utf-8"))
    except Exception as exc:
        out["a19b_v1_report_error"] = f"{type(exc).__name__}: {exc}"
else:
    out["a19b_v1_report"] = None

print(json.dumps(out, indent=2, sort_keys=True))
