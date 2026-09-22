#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import py_compile
import subprocess
import sys

ROOT = Path.cwd()
VENV_PYTHON = ROOT / ".venv" / "bin" / "python"


def run(*args: str, timeout: int = 180) -> dict:
    cp = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)
    return {
        "command": list(args),
        "returncode": cp.returncode,
        "stdout": cp.stdout[-12000:],
        "stderr": cp.stderr[-6000:],
    }


result = {
    "task": "CONTROL-FIX-001-THREE-GATE-VALIDATION",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "openai_api": False,
    "checks": {},
}

# CHECK 1/3: technical compile + targeted unit/regression.
try:
    for rel in (
        "control/validator.py",
        "control/browser_bridge.py",
        "control/executor.py",
        "control/executor_preflight.py",
        "control/jobs/weather_clock_a19c_handoff.py",
    ):
        py_compile.compile(str(ROOT / rel), doraise=True)
    if not VENV_PYTHON.is_file():
        raise RuntimeError("project virtualenv python missing")
    unit = run(
        str(VENV_PYTHON), "-m", "pytest",
        "tests/bridge/test_validator_pytest_venv.py",
        "tests/bridge/test_bridge_runtime_attestation.py",
        "-q",
    )
    check1 = unit["returncode"] == 0
    result["checks"]["check_1_technical"] = {
        "pass": check1,
        "compile_pass": True,
        "pytest": unit,
    }
except Exception as exc:
    check1 = False
    result["checks"]["check_1_technical"] = {
        "pass": False,
        "compile_pass": False,
        "detail": f"{type(exc).__name__}: {exc}",
    }

# CHECK 2/3: explicit fail-closed/adversarial validator regression.
if check1:
    adv = run(
        str(VENV_PYTHON), "-m", "pytest",
        "tests/bridge/test_validator_pytest_venv.py",
        "-q",
    )
    check2 = (
        adv["returncode"] == 0
        and "passed" in adv["stdout"].lower()
    )
    result["checks"]["check_2_fail_closed"] = {
        "pass": check2,
        "system_python_pytest_rejected_by_test": check2,
        "pytest": adv,
    }
else:
    check2 = False
    result["checks"]["check_2_fail_closed"] = {
        "pass": False,
        "status": "SKIPPED_CHECK_1_FAILED",
    }

# CHECK 3/3: realistic control-plane support chain. The outer invocation of
# this script itself is delivered through browser bridge -> Git -> executor.
# Internally we assert sync/preflight/runtime-attestation support tests and the
# previously missing Weather handoff path are present in the synced checkout.
if check1 and check2:
    support = run(
        str(VENV_PYTHON), "-m", "pytest",
        "tests/bridge/test_executor_preflight_atomic_support.py",
        "tests/bridge/test_bridge_runtime_attestation.py",
        "-q",
    )
    handoff_present = (ROOT / "control/jobs/weather_clock_a19c_handoff.py").is_file()
    check3 = support["returncode"] == 0 and handoff_present
    result["checks"]["check_3_realistic_chain"] = {
        "pass": check3,
        "bridge_executor_delivery_required": True,
        "weather_clock_handoff_present": handoff_present,
        "pytest": support,
    }
else:
    check3 = False
    result["checks"]["check_3_realistic_chain"] = {
        "pass": False,
        "status": "SKIPPED_EARLIER_CHECK_FAILED",
    }

all_pass = bool(check1 and check2 and check3)
result["status"] = "PASS" if all_pass else "BLOCKED"
result["next_gate"] = (
    "RERUN_WEATHER_CLOCK_A19C"
    if all_pass else
    "FIX_CONTROL_RUNTIME_VALIDATION"
)
result["economic_conclusion"] = "NO_PROVEN_EDGE"
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if all_pass else 1)
