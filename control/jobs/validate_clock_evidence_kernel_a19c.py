#!/usr/bin/env python3
"""A19C three-gate validation for the latest read-only kernel clock evidence.

CHECK 1/3 technical: compile + latest A19C unit/regression tests.
CHECK 2/3 adversarial/fail-closed tests.
CHECK 3/3 realistic: five real read-only adjtimex()+ntp_gettime() samples.

The real-host probe succeeding is distinct from the clock being accurate enough
for latency evidence.  Therefore local build PASS and clock eligibility are
reported separately.  This script never adjusts the clock and performs no paid,
wallet, trading, or OpenAI API action.
"""
from __future__ import annotations

import json
from pathlib import Path
import py_compile
import subprocess
import sys
import time

ROOT = Path.cwd()
W = ROOT / "control" / "weather"
sys.path.insert(0, str(W))

import clock_evidence_a19c as c  # noqa: E402

MODULE = W / "clock_evidence_a19c.py"
UNIT = W / "test_clock_evidence_a19c.py"
ADV = W / "test_clock_evidence_a19c_adversarial.py"


def run(*args: str, timeout: int = 60):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)


result = {
    "task": "WX-A19C-LATEST-KERNEL-CLOCK-THREE-CHECK",
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "openai_api": False,
    "checks": {},
}

# CHECK 1/3 — latest source + deterministic unit/regression.
try:
    for path in (MODULE, UNIT, ADV):
        py_compile.compile(str(path), doraise=True)
    unit = run(sys.executable, str(UNIT))
    check1 = bool(
        unit.returncode == 0
        and "CLOCK_EVIDENCE_A19C_UNIT_TESTS_PASS" in unit.stdout
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

# CHECK 2/3 — fail closed.
if check1:
    adv = run(sys.executable, str(ADV))
    check2 = bool(
        adv.returncode == 0
        and "CLOCK_EVIDENCE_A19C_ADVERSARIAL_TESTS_PASS" in adv.stdout
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

# CHECK 3/3 — real host path.  Probe completion is the build check; eligibility
# is a separate research gate so a well-functioning fail-closed probe may report
# that the host clock is not currently good enough.
samples = []
if check1 and check2:
    for _ in range(5):
        samples.append(c.clock_health())
        time.sleep(0.05)
    structured = all(
        isinstance(row, dict)
        and row.get("clock_source") == "linux-kernel-adjtimex+ntp_gettime"
        and row.get("read_only") is True
        and "evidence_clock_eligible" in row
        for row in samples
    )
    check3 = bool(len(samples) == 5 and structured)
    result["checks"]["check_3_real_kernel_probe"] = {
        "pass": check3,
        "sample_count": len(samples),
        "samples": samples,
        "semantics": "real read-only host probe; no clock adjustment",
    }
else:
    check3 = False
    result["checks"]["check_3_real_kernel_probe"] = {
        "pass": False,
        "status": "SKIPPED_EARLIER_CHECK_FAILED",
    }

local_pass = bool(check1 and check2 and check3)
eligible_samples = [
    row for row in samples
    if isinstance(row, dict) and row.get("evidence_clock_eligible") is True
]
all_real_samples_eligible = bool(
    check3 and len(eligible_samples) == len(samples) == 5
)

result["local_build_status"] = "PASS" if local_pass else "FAILED"
result["clock_evidence"] = {
    "sample_count": len(samples),
    "eligible_sample_count": len(eligible_samples),
    "all_samples_eligible": all_real_samples_eligible,
    "evidence_clock_eligible": all_real_samples_eligible,
    "eligibility_policy": "all 5 consecutive real read-only samples must be eligible",
}

if not local_pass:
    result["status"] = "BLOCKED_LOCAL_VALIDATION"
    result["next_gate"] = "FIX_A19C_LATEST_LOCAL_VALIDATION"
    code = 1
elif all_real_samples_eligible:
    result["status"] = "PASS_CLOCK_EVIDENCE"
    result["next_gate"] = "EXTERNAL_UTC_CROSSCHECK_THEN_NOAA_MADIS_LDM_ACCESS_OR_RUNTIME"
    code = 0
else:
    result["status"] = "BLOCKED_REAL_CLOCK_EVIDENCE"
    result["next_gate"] = "CLOCK_EVIDENCE_TRANSPORT_OR_SYSTEM_SYNC"
    code = 0

print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(code)
