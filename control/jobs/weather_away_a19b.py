#!/usr/bin/env python3
"""Weather away supervisor — public-source successor to the blocked MADIS LDM lane.

The old A19B LDM adapter remains preserved and is still regression-tested because
it contains useful provenance/clock work. It is no longer the operational next
gate: direct MADIS LDM access is unavailable for this deployment. The active
zero-cost lane is prospective public-source timing + Kalshi market reaction.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "evidence" / "weather"
EVIDENCE.mkdir(parents=True, exist_ok=True)
PROJECT_PYTHON = ROOT / ".venv" / "bin" / "python"
PYTHON = str(PROJECT_PYTHON if PROJECT_PYTHON.is_file() else Path(sys.executable))


def run(*args: str, timeout: int = 600) -> dict:
    try:
        cp = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)
        return {
            "command": list(args),
            "returncode": cp.returncode,
            "stdout": cp.stdout[-30000:],
            "stderr": cp.stderr[-15000:],
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": list(args),
            "returncode": 124,
            "stdout": (exc.stdout or "")[-30000:] if isinstance(exc.stdout, str) else "",
            "stderr": ((exc.stderr or "") + "\nTIMEOUT")[-15000:] if isinstance(exc.stderr, str) else "TIMEOUT",
            "timed_out": True,
        }


def parse_json(text: str) -> dict:
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


result = {
    "task": "WEATHER-AWAY-PUBLIC-SOURCE-SUCCESSOR",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "python": PYTHON,
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "private_madis_access": False,
    "economic_conclusion": "NO_PROVEN_EDGE",
    "steps": {},
}

# Preserve technical knowledge from A19B, but do not let unavailable private LDM
# access block the current operational weather lane.
legacy = run(PYTHON, "control/jobs/validate_madis_ldm_a19b.py", timeout=300)
legacy_obj = parse_json(legacy["stdout"])
result["steps"]["legacy_a19b_regression"] = {
    "runner": legacy,
    "parsed": legacy_obj,
    "blocking": False,
    "interpretation": "Preserved regression only; private MADIS LDM is not the active next gate.",
}

public_validation = run(PYTHON, "control/jobs/validate_public_metar_race.py", timeout=180)
public_obj = parse_json(public_validation["stdout"])
public_pass = bool(public_validation["returncode"] == 0 and public_obj.get("status") == "PASS")
result["steps"]["public_source_three_gate_validation"] = {
    "runner": public_validation,
    "parsed": public_obj,
    "blocking": True,
}

if public_pass:
    analysis = run(PYTHON, "control/weather/analyze_public_metar_race.py", timeout=60)
    analysis_obj = parse_json(analysis["stdout"])
    result["steps"]["public_source_analysis"] = {
        "runner": analysis,
        "parsed": analysis_obj,
    }
else:
    result["steps"]["public_source_analysis"] = {"status": "SKIPPED_PUBLIC_VALIDATION_NOT_PASS"}

# Existing market side remains independently valuable: open-event discovery and
# authenticated read-only Kalshi WebSocket capture. Do a short prospective cycle
# only when public-source validation is healthy. Missing local read-only creds is
# recorded as a blocker, never silently ignored.
if public_pass:
    market = run(
        PYTHON,
        "control/weather/e401_prospective_supervisor.py",
        "--once",
        "--capture-sec",
        "20",
        timeout=90,
    )
    result["steps"]["kalshi_readonly_market_capture"] = {
        "runner": market,
        "parsed": parse_json(market["stdout"]),
        "required_for_source_collection": False,
        "required_for_market_edge_gate": True,
    }
else:
    result["steps"]["kalshi_readonly_market_capture"] = {"status": "SKIPPED_PUBLIC_VALIDATION_NOT_PASS"}

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

result["status"] = "PASS" if public_pass else "BLOCKED_PUBLIC_SOURCE_VALIDATION"
result["next_gate"] = (
    "CONTINUOUS_PUBLIC_SOURCE_RACE_AND_POINT_IN_TIME_MARKET_REACTION"
    if public_pass else
    "FIX_PUBLIC_SOURCE_THREE_GATE_VALIDATION"
)
result["legacy_madis_ldm_status"] = "PRESERVED_BUT_ACCESS_BLOCKED_FOR_CURRENT_DEPLOYMENT"

out = EVIDENCE / "WEATHER-AWAY-A19B-latest.json"
out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({
    "status": result["status"],
    "report": str(out),
    "public_source_validation_pass": public_pass,
    "legacy_a19b_regression_pass": bool(legacy["returncode"] == 0 and legacy_obj.get("status") == "PASS"),
    "next_gate": result["next_gate"],
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
}, indent=2, sort_keys=True))
raise SystemExit(0 if public_pass else 1)
