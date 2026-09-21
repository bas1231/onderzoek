#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

MAIN = Path.home() / "prediction_research"
WEATHER = Path.home() / "prediction_research_weather"
RESULT = MAIN / "control/results/WEATHER-A19B-V2-GATE-009/RESULT.json"
V1_PROOF = WEATHER / "evidence/weather/A19B_V1_IMMUTABLE_PROOF.json"
V1_LATEST = WEATHER / "evidence/weather/WEATHER-AWAY-A19B-latest.json"


def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception as exc:
        return {"_load_error": f"{type(exc).__name__}: {exc}"}


def git(args: list[str], cwd: Path) -> str:
    try:
        cp = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, timeout=20)
        return (cp.stdout or cp.stderr).strip()
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"


obj = load(RESULT)
stdout_text = obj.get("stdout") if isinstance(obj.get("stdout"), str) else ""
try:
    parsed_stdout = json.loads(stdout_text) if stdout_text else {}
except Exception as exc:
    parsed_stdout = {"_parse_error": f"{type(exc).__name__}: {exc}", "raw": stdout_text[-20000:]}

payload = {
    "task": "WEATHER-INSPECT-V2-FAILURE-009",
    "source_result_path": str(RESULT),
    "source_result_exists": RESULT.is_file(),
    "source_result": obj.get("result"),
    "source_stdout_parsed": parsed_stdout,
    "source_stderr": obj.get("stderr"),
    "weather_head": git(["rev-parse", "HEAD"], WEATHER) if WEATHER.is_dir() else None,
    "weather_branch": git(["branch", "--show-current"], WEATHER) if WEATHER.is_dir() else None,
    "weather_tracked_status": git(["status", "--porcelain", "--untracked-files=no"], WEATHER) if WEATHER.is_dir() else None,
    "v1_immutable_proof": load(V1_PROOF) if V1_PROOF.is_file() else None,
    "v1_latest_status": load(V1_LATEST).get("status") if V1_LATEST.is_file() else None,
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
}
print(json.dumps(payload, indent=2, sort_keys=True))
