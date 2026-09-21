#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
from datetime import datetime, timezone

ROOT = Path.cwd()
EVIDENCE = ROOT / "evidence" / "weather"
EVIDENCE.mkdir(parents=True, exist_ok=True)
PROJECT_PYTHON = Path.home() / "prediction_research" / ".venv" / "bin" / "python"
PYTHON = str(PROJECT_PYTHON if PROJECT_PYTHON.is_file() else Path("python3"))


def run(*args: str, timeout: int = 600) -> dict:
    try:
        cp = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)
        return {
            "command": list(args),
            "returncode": cp.returncode,
            "stdout": cp.stdout[-20000:],
            "stderr": cp.stderr[-10000:],
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": list(args),
            "returncode": 124,
            "stdout": (exc.stdout or "")[-20000:] if isinstance(exc.stdout, str) else "",
            "stderr": ((exc.stderr or "") + "\nTIMEOUT")[-10000:] if isinstance(exc.stderr, str) else "TIMEOUT",
            "timed_out": True,
        }


def parse_json(text: str) -> dict:
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


result = {
    "task": "WEATHER-AWAY-A19B",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "python": PYTHON,
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "economic_conclusion": "NO_PROVEN_EDGE",
    "steps": {},
}

validation = run(PYTHON, "control/jobs/validate_madis_ldm_a19b.py", timeout=300)
validation_obj = parse_json(validation["stdout"])
result["steps"]["a19b_three_gate_validation"] = {
    "runner": validation,
    "parsed": validation_obj,
}
validation_pass = bool(validation["returncode"] == 0 and validation_obj.get("status") == "PASS")

if validation_pass:
    refresh = run(PYTHON, "control/jobs/run_weather_a18_a19.py", timeout=600)
    result["steps"]["a18_a19_refresh"] = {
        "runner": refresh,
        "parsed": parse_json(refresh["stdout"]),
    }
else:
    result["steps"]["a18_a19_refresh"] = {"status": "SKIPPED_A19B_VALIDATION_NOT_PASS"}

clock = {}
if shutil.which("chronyc"):
    clock["chronyc_tracking"] = run("chronyc", "tracking", "-n", timeout=10)
else:
    clock["chronyc_tracking"] = {"status": "NOT_INSTALLED"}
if shutil.which("timedatectl"):
    clock["timedatectl_ntp"] = run("timedatectl", "show", "-p", "NTPSynchronized", "--value", timeout=10)
else:
    clock["timedatectl_ntp"] = {"status": "NOT_AVAILABLE"}
result["steps"]["clock_readiness"] = clock

result["status"] = "PASS" if validation_pass else "BLOCKED_A19B_VALIDATION"
result["next_gate"] = (
    "NOAA_MADIS_LDM_ACCESS_AND_QUEUE_NATIVE_A19B_V2"
    if validation_pass else
    "FIX_A19B_THREE_GATE_VALIDATION"
)

out = EVIDENCE / "WEATHER-AWAY-A19B-latest.json"
out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({
    "status": result["status"],
    "report": str(out),
    "a19b_validation_pass": validation_pass,
    "next_gate": result["next_gate"],
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
}, indent=2, sort_keys=True))
raise SystemExit(0 if validation_pass else 1)
