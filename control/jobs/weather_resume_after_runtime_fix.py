#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path.cwd()
PYTHON = ROOT / ".venv" / "bin" / "python"
RUNTIME = ROOT / "control/jobs/validate_control_runtime_fix.py"
WEATHER = ROOT / "control/jobs/weather_clock_a19c_handoff.py"


def run(script: Path, timeout: int) -> dict:
    cp = subprocess.run(
        [str(PYTHON), str(script.relative_to(ROOT))],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    try:
        parsed = json.loads(cp.stdout)
        if not isinstance(parsed, dict):
            parsed = {}
    except Exception:
        parsed = {}
    return {
        "returncode": cp.returncode,
        "parsed": parsed,
        "stdout": cp.stdout[-16000:],
        "stderr": cp.stderr[-8000:],
    }


def emit(payload: dict, code: int) -> None:
    payload.update({
        "economic_conclusion": "NO_PROVEN_EDGE",
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
        "openai_api": False,
    })
    print(json.dumps(payload, indent=2, sort_keys=True))
    raise SystemExit(code)


if not PYTHON.is_file():
    emit({"status": "BLOCKED", "next_gate": "PROJECT_VENV_MISSING"}, 2)
if not RUNTIME.is_file():
    emit({"status": "BLOCKED", "next_gate": "CONTROL_RUNTIME_VALIDATOR_MISSING"}, 3)
if not WEATHER.is_file():
    emit({"status": "BLOCKED", "next_gate": "WEATHER_A19C_HANDOFF_MISSING"}, 4)

runtime = run(RUNTIME, 300)
runtime_ok = bool(
    runtime["returncode"] == 0
    and runtime["parsed"].get("status") == "PASS"
)

if not runtime_ok:
    emit({
        "status": "BLOCKED_CONTROL_RUNTIME",
        "next_gate": runtime["parsed"].get("next_gate") or "FIX_CONTROL_RUNTIME_VALIDATION",
        "control_runtime": runtime,
        "weather_started": False,
    }, 5)

weather = run(WEATHER, 300)
weather_ok = bool(
    weather["returncode"] == 0
    and weather["parsed"].get("status") == "PASS"
)

payload = {
    "status": "PASS" if weather_ok else "BLOCKED_WEATHER_GATE",
    "control_runtime": runtime,
    "weather": weather,
    "weather_started": True,
    "next_gate": weather["parsed"].get("next_gate") or "A19C_RESULT_MISSING_NEXT_GATE",
}

emit(payload, 0 if weather_ok else 6)
