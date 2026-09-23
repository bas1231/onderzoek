#!/usr/bin/env python3
"""Three-gate passive clock diagnostic for Weather A19B-v2.

A blocked clock-evidence gate is a valid diagnostic outcome, not a build failure.
No installation, service changes, time changes, network calls, trading, wallet or
paid actions are performed.
"""
from __future__ import annotations

import json
from pathlib import Path
import py_compile
import subprocess
import sys

ROOT = Path.cwd()
WEATHER = ROOT / "control" / "weather"
CORE = WEATHER / "weather_clock_diag_a19b_v2.py"
UNIT = WEATHER / "test_weather_clock_diag_a19b_v2.py"
ADV = WEATHER / "test_weather_clock_diag_a19b_v2_adversarial.py"

sys.path.insert(0, str(WEATHER))
import weather_clock_diag_a19b_v2 as clockdiag  # noqa: E402


def run(*args: str, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)


result = {
    "task": "WEATHER-A19B-V2-CLOCK-DIAG-THREE-CHECK",
    "passive_only": True,
    "system_modified": False,
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "economic_conclusion": "NO_PROVEN_EDGE",
    "checks": {},
}

# CHECK 1/3 — compile + unit/regression.
try:
    for path in (CORE, UNIT, ADV):
        py_compile.compile(str(path), doraise=True)
    unit = run(sys.executable, str(UNIT))
    check1 = bool(
        unit.returncode == 0
        and "WEATHER_CLOCK_DIAG_A19B_V2_UNIT_TESTS_PASS" in unit.stdout
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

# CHECK 2/3 — explicit fail-closed cases.
if check1:
    adv = run(sys.executable, str(ADV))
    check2 = bool(
        adv.returncode == 0
        and "WEATHER_CLOCK_DIAG_A19B_V2_ADVERSARIAL_TESTS_PASS" in adv.stdout
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

# CHECK 3/3 — passive diagnostic on this actual machine.
if check1 and check2:
    try:
        actual = clockdiag.collect_clock_evidence()
        assessment = actual.get("assessment") or {}
        actual_status = assessment.get("status")
        check3 = bool(
            actual.get("passive_only") is True
            and actual.get("system_modified") is False
            and actual_status in {"PASS_CLOCK_EVIDENCE", "BLOCKED_CLOCK_EVIDENCE"}
        )
        result["checks"]["check_3_actual_machine"] = {
            "pass": check3,
            "diagnostic_status": actual_status,
            "clock_source": assessment.get("clock_source"),
            "clock_offset_ms": assessment.get("clock_offset_ms"),
            "clock_uncertainty_ms": assessment.get("clock_uncertainty_ms"),
            "clock_evidence_eligible": assessment.get("clock_evidence_eligible"),
            "ntp_synchronized": assessment.get("ntp_synchronized"),
            "ntp_enabled": assessment.get("ntp_enabled"),
            "systemd_timesync_marker": assessment.get("systemd_timesync_marker"),
            "reason": assessment.get("reason"),
            "inventory": actual.get("inventory"),
        }
    except Exception as exc:
        check3 = False
        actual = {}
        assessment = {}
        result["checks"]["check_3_actual_machine"] = {
            "pass": False,
            "detail": f"{type(exc).__name__}: {exc}",
        }
else:
    check3 = False
    actual = {}
    assessment = {}
    result["checks"]["check_3_actual_machine"] = {
        "pass": False,
        "status": "SKIPPED_EARLIER_CHECK_FAILED",
    }

local_pass = bool(check1 and check2 and check3)
result["status"] = "PASS_LOCAL_DIAGNOSTIC" if local_pass else "BLOCKED_LOCAL_VALIDATION"
result["clock_evidence_eligible"] = bool(assessment.get("clock_evidence_eligible") is True)
result["clock_source"] = assessment.get("clock_source")
result["clock_offset_ms"] = assessment.get("clock_offset_ms")
result["clock_uncertainty_ms"] = assessment.get("clock_uncertainty_ms")

if not local_pass:
    result["next_gate"] = "FIX_CLOCK_DIAGNOSTIC_FAILED_CHECK"
elif result["clock_evidence_eligible"]:
    result["next_gate"] = "CLOCK_EVIDENCE_SATISFIED"
else:
    result["next_gate"] = "BLOCKED_CLOCK_EVIDENCE"

print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if local_pass else 1)
