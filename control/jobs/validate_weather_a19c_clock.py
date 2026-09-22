#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import py_compile
import subprocess
import sys

ROOT = Path.cwd()
JOBS = ROOT / "control" / "jobs"
WEATHER = ROOT / "control" / "weather"
DIAG = JOBS / "weather_a19c_clock_diagnostic.py"
UNIT = WEATHER / "test_weather_a19c_clock_diagnostic.py"
ADV = WEATHER / "test_weather_a19c_clock_diagnostic_adversarial.py"


def run(*args: str, timeout: int = 60):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)


result = {
    "task": "WEATHER-A19C-CLOCK-EVIDENCE-THREE-CHECK",
    "checks": {},
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "economic_conclusion": "NO_PROVEN_EDGE",
}

# CHECK 1/3 — technical.
try:
    for path in (DIAG, UNIT, ADV):
        py_compile.compile(str(path), doraise=True)
    unit = run(sys.executable, str(UNIT))
    check1 = unit.returncode == 0 and "WEATHER_A19C_CLOCK_UNIT_TESTS_PASS" in unit.stdout
    result["checks"]["check_1_technical"] = {
        "pass": check1,
        "compile_pass": True,
        "stdout": unit.stdout.strip(),
        "stderr": unit.stderr[-3000:],
    }
except Exception as exc:
    check1 = False
    result["checks"]["check_1_technical"] = {
        "pass": False,
        "compile_pass": False,
        "detail": f"{type(exc).__name__}: {exc}",
    }

# CHECK 2/3 — adversarial/fail-closed.
if check1:
    adv = run(sys.executable, str(ADV))
    check2 = adv.returncode == 0 and "WEATHER_A19C_CLOCK_ADVERSARIAL_TESTS_PASS" in adv.stdout
    result["checks"]["check_2_fail_closed"] = {
        "pass": check2,
        "stdout": adv.stdout.strip(),
        "stderr": adv.stderr[-3000:],
    }
else:
    check2 = False
    result["checks"]["check_2_fail_closed"] = {"pass": False, "status": "SKIPPED_CHECK_1_FAILED"}

# CHECK 3/3 — real host diagnostic. A blocked clock gate is a valid result.
if check1 and check2:
    diag = run(sys.executable, str(DIAG), timeout=30)
    try:
        obj = json.loads(diag.stdout)
    except Exception:
        obj = {}
    gate = obj.get("clock_gate_status")
    classification = obj.get("clock_classification") or {}
    check3 = bool(
        diag.returncode == 0
        and obj.get("status") == "COMPLETED_DIAGNOSTIC"
        and gate in {"PASS_CLOCK_EVIDENCE", "BLOCKED_CLOCK_EVIDENCE"}
        and obj.get("mutation_performed") is False
        and obj.get("live_trading") is False
        and obj.get("paid_action") is False
        and obj.get("wallet_action") is False
        and obj.get("economic_conclusion") == "NO_PROVEN_EDGE"
        and isinstance(classification.get("reasons"), list)
    )
    if gate == "BLOCKED_CLOCK_EVIDENCE":
        check3 = bool(check3 and classification.get("clock_evidence_eligible") is False)
    if gate == "PASS_CLOCK_EVIDENCE":
        check3 = bool(check3 and classification.get("clock_evidence_eligible") is True)
    result["checks"]["check_3_real_host"] = {
        "pass": check3,
        "diagnostic_exit_code": diag.returncode,
        "clock_gate_status": gate,
        "next_gate": obj.get("next_gate"),
        "clock_health": obj.get("clock_health"),
        "clock_classification": classification,
        "readonly_inventory": obj.get("readonly_inventory"),
        "stderr": diag.stderr[-3000:],
    }
else:
    check3 = False
    result["checks"]["check_3_real_host"] = {"pass": False, "status": "SKIPPED_EARLIER_CHECK_FAILED"}

all_pass = bool(check1 and check2 and check3)
real = result["checks"].get("check_3_real_host") or {}
gate = real.get("clock_gate_status")
result["status"] = "PASS_LOCAL_VALIDATION" if all_pass else "BLOCKED_LOCAL_VALIDATION"
result["clock_gate_status"] = gate if all_pass else None
result["next_gate"] = (
    real.get("next_gate")
    if all_pass
    else "FIX_A19C_CLOCK_VALIDATION"
)
result["terminal_for_current_authorization"] = bool(
    all_pass and gate == "BLOCKED_CLOCK_EVIDENCE"
)
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if all_pass else 1)
