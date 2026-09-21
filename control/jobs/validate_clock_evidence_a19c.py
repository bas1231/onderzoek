#!/usr/bin/env python3
"""A19C three-gate validation for clock evidence.

CHECK 1/3 technical: compile + deterministic unit tests.
CHECK 2/3 adversarial/fail-closed tests.
CHECK 3/3 realistic/prospective: live SNTP consensus from public servers.

No system clock is changed. No paid service/API is used.
"""
from __future__ import annotations

import json
from pathlib import Path
import py_compile
import subprocess
import sys

ROOT = Path.cwd()
WEATHER = ROOT / "control" / "weather"
sys.path.insert(0, str(WEATHER))

import clock_evidence_sntp_a19c as c  # noqa: E402

MODULE = WEATHER / "clock_evidence_sntp_a19c.py"
UNIT = WEATHER / "test_clock_evidence_sntp_a19c.py"
ADV = WEATHER / "test_clock_evidence_sntp_a19c_adversarial.py"
WRAPPER = WEATHER / "madis_ldm_queue_native_a19b_v2_clocked.py"


def run(*args: str, timeout: int = 90):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)


result = {
    "task": "WEATHER-CLOCK-EVIDENCE-A19C-THREE-CHECK",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "openai_api": False,
    "economic_conclusion": "NO_PROVEN_EDGE",
    "checks": {},
}

try:
    for path in (MODULE, UNIT, ADV, WRAPPER):
        py_compile.compile(str(path), doraise=True)
    unit = run(sys.executable, str(UNIT), timeout=60)
    check1 = bool(
        unit.returncode == 0
        and "CLOCK_EVIDENCE_SNTP_A19C_UNIT_TESTS_PASS" in unit.stdout
    )
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

if check1:
    adv = run(sys.executable, str(ADV), timeout=60)
    check2 = bool(
        adv.returncode == 0
        and "CLOCK_EVIDENCE_SNTP_A19C_ADVERSARIAL_TESTS_PASS" in adv.stdout
    )
    result["checks"]["check_2_fail_closed"] = {
        "pass": check2,
        "stdout": adv.stdout.strip(),
        "stderr": adv.stderr[-3000:],
    }
else:
    check2 = False
    result["checks"]["check_2_fail_closed"] = {
        "pass": False,
        "status": "SKIPPED_CHECK_1_FAILED",
    }

clock = {}
if check1 and check2:
    try:
        clock = c.collect_clock_evidence()
        check3 = clock.get("evidence_clock_eligible") is True
        result["checks"]["check_3_live_clock_evidence"] = {
            "pass": check3,
            "clock": clock,
            "semantics": "live SNTP evidence; probe only, system clock not modified",
        }
    except Exception as exc:
        check3 = False
        result["checks"]["check_3_live_clock_evidence"] = {
            "pass": False,
            "detail": f"{type(exc).__name__}: {exc}",
        }
else:
    check3 = False
    result["checks"]["check_3_live_clock_evidence"] = {
        "pass": False,
        "status": "SKIPPED_EARLIER_CHECK_FAILED",
    }

local_build = bool(check1 and check2)
result["local_build_status"] = "PASS" if local_build else "FAILED"
result["clock_readiness"] = clock

if not local_build:
    result["status"] = "BLOCKED_LOCAL_VALIDATION"
    result["next_gate"] = "FIX_A19C_LOCAL_VALIDATION"
    exit_code = 1
elif check3:
    result["status"] = "PASS_CLOCK_EVIDENCE"
    result["next_gate"] = "BLOCKED_NOAA_MADIS_LDM_ACCESS_OR_RUNTIME"
    exit_code = 0
else:
    # This is a completed research gate, not a false technical PASS: local code
    # is proven but the current environment did not yield <=100ms clock proof.
    result["status"] = "BLOCKED_REAL_CLOCK_EVIDENCE"
    result["next_gate"] = "CLOCK_EVIDENCE_TRANSPORT_OR_SYSTEM_SYNC"
    exit_code = 0

result["terminal_for_current_clock_gate"] = bool(local_build and not check3)
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(exit_code)
