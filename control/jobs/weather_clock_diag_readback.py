#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

MAIN = Path.home() / "prediction_research"
WEATHER = Path.home() / "prediction_research_weather"
TASK_ID = "WEATHER-CLOCK-GATE-029-DIAG-030"


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 15) -> dict:
    try:
        cp = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=timeout)
        return {
            "command": cmd,
            "returncode": cp.returncode,
            "stdout": cp.stdout[-12000:],
            "stderr": cp.stderr[-6000:],
        }
    except Exception as exc:
        return {
            "command": cmd,
            "returncode": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def read_json(path: Path) -> dict:
    if not path.is_file():
        return {"exists": False, "path": str(path)}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return {"exists": True, "path": str(path), "json": obj}
    except Exception as exc:
        return {
            "exists": True,
            "path": str(path),
            "parse_error": f"{type(exc).__name__}: {exc}",
            "text_tail": path.read_text(encoding="utf-8", errors="replace")[-12000:],
        }

result = {
    "task": "WEATHER-CLOCK-GATE-030-READBACK-031",
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "local_result": read_json(MAIN / "control" / "results" / TASK_ID / "RESULT.json"),
    "weather_result": read_json(WEATHER / "control" / "results" / TASK_ID / "RESULT.json"),
    "weather_evidence_latest": read_json(WEATHER / "evidence" / "weather" / "WEATHER-AWAY-A19B-latest.json"),
    "weather_branch": run(["git", "branch", "--show-current"], cwd=WEATHER),
    "weather_head": run(["git", "rev-parse", "HEAD"], cwd=WEATHER),
    "weather_status": run(["git", "status", "--porcelain"], cwd=WEATHER),
    "chronyc_path": shutil.which("chronyc"),
    "chronyd_path": shutil.which("chronyd"),
    "timedatectl_path": shutil.which("timedatectl"),
}

if shutil.which("chronyc"):
    result["chronyc_tracking"] = run(["chronyc", "tracking", "-n"])
if shutil.which("timedatectl"):
    result["timedatectl_ntp"] = run(["timedatectl", "show", "-p", "NTPSynchronized", "--value"])
    result["timedatectl_timesync"] = run(["timedatectl", "show-timesync", "--all"])

print(json.dumps(result, indent=2, sort_keys=True))
