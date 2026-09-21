#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

MAIN = Path.home() / "prediction_research"
WEATHER = Path.home() / "prediction_research_weather"
PYTHON = MAIN / ".venv/bin/python"
BASE = MAIN / "control/jobs/weather_handoff_a19b_min.py"
A19C = WEATHER / "control/jobs/validate_clock_evidence_a19c.py"
KERNEL_PROBE = WEATHER / "control/jobs/probe_kernel_clock_a19b_v2.py"


def run(*args: str, cwd: Path, timeout: int = 1800):
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=timeout)


def parse_obj(text: str) -> dict:
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def emit(payload: dict, code: int = 0):
    payload.update({
        "economic_conclusion": "NO_PROVEN_EDGE",
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
        "openai_api": False,
    })
    print(json.dumps(payload, indent=2, sort_keys=True))
    raise SystemExit(code)


for path, reason in (
    (PYTHON, "PREDICTION_VENV_PYTHON_MISSING"),
    (BASE, "A19B_BASE_HANDOFF_MISSING"),
):
    if not path.is_file():
        emit({"status": "BLOCKED", "next_gate": reason}, 2)

# Gate 1+2: preserve the existing immutable-proof-aware A19B-v1/v2 handoff.
base = run(str(PYTHON), str(BASE), cwd=MAIN, timeout=1500)
base_obj = parse_obj(base.stdout)
steps: dict[str, object] = {
    "a19b_base": {
        "returncode": base.returncode,
        "status": base_obj.get("status"),
        "next_gate": base_obj.get("next_gate"),
        "weather_head": base_obj.get("weather_head"),
        "steps": base_obj.get("steps"),
        "stderr": base.stderr[-5000:],
    }
}

if base.returncode != 0:
    emit({
        "status": "BLOCKED_LOCAL_VALIDATION",
        "steps": steps,
        "next_gate": base_obj.get("next_gate") or "FIX_A19B_BASE_GATE",
        "terminal_for_current_authorization": False,
    }, 3)

next_gate = str(base_obj.get("next_gate") or "UNKNOWN_A19B_BASE_GATE")
if next_gate == "BLOCKED_NOAA_MADIS_LDM_ACCESS_OR_RUNTIME":
    emit({
        "status": "COMPLETED_LOCAL_RESEARCH_GATE",
        "steps": steps,
        "next_gate": next_gate,
        "terminal_for_current_authorization": True,
    }, 0)

if next_gate != "BLOCKED_CLOCK_EVIDENCE":
    emit({
        "status": "COMPLETED_LOCAL_RESEARCH_GATE",
        "steps": steps,
        "next_gate": next_gate,
        "terminal_for_current_authorization": next_gate != "READY_FOR_REAL_QUEUE_NATIVE_CAPTURE",
    }, 0)

# Gate 3: A19C proves clock evidence independently of A19B-v2 plumbing.
if not A19C.is_file():
    emit({
        "status": "BLOCKED_LOCAL_BUILD",
        "steps": steps,
        "next_gate": "A19C_VALIDATOR_MISSING",
    }, 4)

a19c = run(str(PYTHON), str(A19C.relative_to(WEATHER)), cwd=WEATHER, timeout=300)
a19c_obj = parse_obj(a19c.stdout)
steps["a19c_clock"] = {
    "returncode": a19c.returncode,
    "status": a19c_obj.get("status"),
    "next_gate": a19c_obj.get("next_gate"),
    "checks": a19c_obj.get("checks"),
    "clock_readiness": a19c_obj.get("clock_readiness"),
    "stderr": a19c.stderr[-5000:],
}

if a19c.returncode != 0 or a19c_obj.get("local_build_status") != "PASS":
    emit({
        "status": "BLOCKED_LOCAL_VALIDATION",
        "steps": steps,
        "next_gate": a19c_obj.get("next_gate") or "FIX_A19C_LOCAL_VALIDATION",
        "terminal_for_current_authorization": False,
    }, 5)

clock_gate = str(a19c_obj.get("next_gate") or "UNKNOWN_A19C_GATE")
if a19c_obj.get("status") == "PASS_CLOCK_EVIDENCE":
    emit({
        "status": "COMPLETED_LOCAL_RESEARCH_GATE",
        "steps": steps,
        "next_gate": "BLOCKED_NOAA_MADIS_LDM_ACCESS_OR_RUNTIME",
        "terminal_for_current_authorization": True,
    }, 0)

# Diagnostic only: never promote kernel adjtimex data to eligibility by itself.
if KERNEL_PROBE.is_file():
    probe = run(str(PYTHON), str(KERNEL_PROBE.relative_to(WEATHER)), cwd=WEATHER, timeout=90)
    probe_obj = parse_obj(probe.stdout)
    steps["kernel_clock_probe"] = {
        "returncode": probe.returncode,
        "status": probe_obj.get("status"),
        "decision": probe_obj.get("decision"),
        "observed": probe_obj.get("observed"),
        "valid_sample_count": probe_obj.get("valid_sample_count"),
        "timedatectl_ntp_synchronized": probe_obj.get("timedatectl_ntp_synchronized"),
        "stderr": probe.stderr[-5000:],
        "semantics": "diagnostic only; no eligibility promotion",
    }

emit({
    "status": "COMPLETED_LOCAL_RESEARCH_GATE",
    "steps": steps,
    "next_gate": clock_gate,
    "terminal_for_current_authorization": True,
}, 0)
