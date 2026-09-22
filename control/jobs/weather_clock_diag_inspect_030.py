#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path.cwd()
HOME = Path.home()
WEATHER = HOME / "prediction_research_weather"
RESULT = ROOT / "control/results/WEATHER-A19B-V2-CLOCK-DIAG-029/RESULT.json"
WEATHER_REPORTS = [
    WEATHER / "evidence/weather/WEATHER-AWAY-A19B-latest.json",
    WEATHER / "evidence/weather/WEATHER-A19B-V2-latest.json",
    WEATHER / "evidence/weather/A19B_V2-latest.json",
]


def run(*args: str, cwd: Path | None = None, timeout: int = 15) -> dict:
    try:
        cp = subprocess.run(args, cwd=cwd or ROOT, text=True, capture_output=True, timeout=timeout)
        return {
            "returncode": cp.returncode,
            "stdout": cp.stdout[-12000:],
            "stderr": cp.stderr[-6000:],
        }
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def read_json(path: Path):
    if not path.is_file():
        return {"exists": False, "path": str(path)}
    try:
        return {"exists": True, "path": str(path), "json": json.loads(path.read_text(encoding="utf-8"))}
    except Exception as exc:
        return {"exists": True, "path": str(path), "parse_error": f"{type(exc).__name__}: {exc}"}

out = {
    "task": "WEATHER-A19B-V2-CLOCK-DIAG-INSPECT-030",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "economic_conclusion": "NO_PROVEN_EDGE",
    "source_result_029": read_json(RESULT),
    "weather_reports": [read_json(p) for p in WEATHER_REPORTS],
    "clock": {
        "chronyc_path": shutil.which("chronyc"),
        "timedatectl_path": shutil.which("timedatectl"),
    },
    "ldm": {
        "pqact_path": shutil.which("pqact"),
        "pqcheck_path": shutil.which("pqcheck"),
        "ldmd_path": shutil.which("ldmd"),
        "ldmadmin_path": shutil.which("ldmadmin"),
    },
}

if WEATHER.is_dir():
    out["weather_worktree"] = {
        "branch": run("git", "branch", "--show-current", cwd=WEATHER),
        "head": run("git", "rev-parse", "HEAD", cwd=WEATHER),
        "status": run("git", "status", "--porcelain", cwd=WEATHER),
    }
else:
    out["weather_worktree"] = {"exists": False}

if shutil.which("chronyc"):
    out["clock"]["chronyc_tracking"] = run("chronyc", "tracking", "-n")
if shutil.which("timedatectl"):
    out["clock"]["ntp_synchronized"] = run("timedatectl", "show", "-p", "NTPSynchronized", "--value")
    out["clock"]["time_status"] = run("timedatectl", "status")

print(json.dumps(out, indent=2, sort_keys=True))
