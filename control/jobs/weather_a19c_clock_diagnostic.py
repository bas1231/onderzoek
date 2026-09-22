#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path.cwd()
WEATHER = Path.home() / "prediction_research_weather"
TARGET = ROOT / "control/results/WEATHER-A19C-CLOCK-GATE-032/RESULT.json"
WEATHER_REPORTS = [
    WEATHER / "evidence/weather/WEATHER-AWAY-A19B-latest.json",
    WEATHER / "evidence/weather/WEATHER-A19C-CLOCK-latest.json",
    WEATHER / "evidence/weather/A19C_CLOCK-latest.json",
]


def run(*args: str) -> dict:
    try:
        cp = subprocess.run(args, text=True, capture_output=True, timeout=10)
        return {"returncode": cp.returncode, "stdout": cp.stdout[-8000:], "stderr": cp.stderr[-4000:]}
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def read_json(path: Path):
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"parse_error": f"{type(exc).__name__}: {exc}", "raw_tail": path.read_text(encoding="utf-8", errors="replace")[-8000:]}

out = {
    "task": "WEATHER-A19C-CLOCK-DIAGNOSTIC",
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "source_result": read_json(TARGET),
    "source_result_path": str(TARGET),
    "clock_tools": {
        "chronyc": shutil.which("chronyc"),
        "timedatectl": shutil.which("timedatectl"),
    },
    "clock_commands": {},
    "weather_reports": {},
}

if shutil.which("chronyc"):
    out["clock_commands"]["chronyc_tracking"] = run("chronyc", "tracking", "-n")
if shutil.which("timedatectl"):
    out["clock_commands"]["timedatectl_sync"] = run("timedatectl", "show", "-p", "NTPSynchronized", "--value")
    out["clock_commands"]["timedatectl_status"] = run("timedatectl", "status")

for path in WEATHER_REPORTS:
    if path.is_file():
        out["weather_reports"][str(path)] = read_json(path)

if WEATHER.is_dir():
    out["weather_git"] = {
        "branch": run("git", "-C", str(WEATHER), "branch", "--show-current"),
        "head": run("git", "-C", str(WEATHER), "rev-parse", "HEAD"),
        "status": run("git", "-C", str(WEATHER), "status", "--porcelain", "--untracked-files=no"),
    }

print(json.dumps(out, indent=2, sort_keys=True))
