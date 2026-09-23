#!/usr/bin/env python3
"""Three-gate validation for A19B-v2 direct NIST UTC clock evidence."""
from __future__ import annotations

import json
from pathlib import Path
import py_compile
import subprocess
import sys

ROOT = Path.cwd()
WEATHER = ROOT / "control" / "weather"
sys.path.insert(0, str(WEATHER))

import nist_ntp_clock_a19b_v2 as ntp

FILES = [
    WEATHER / "nist_ntp_clock_a19b_v2.py",
    WEATHER / "test_nist_ntp_clock_a19b_v2.py",
    WEATHER / "test_nist_ntp_clock_a19b_v2_adversarial.py",
]


def run(*args: str, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)


result = {
    "task": "WX-A19B-V2-NIST-NTP-CLOCK-THREE-CHECK",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "changes_system_clock": False,
    "economic_conclusion": "NO_PROVEN_EDGE",
    "checks": {},
}

# CHECK 1/3 — compile + deterministic unit/regression.
try:
    for path in FILES:
        py_compile.compile(str(path), doraise=True)
    unit = run(sys.executable, str(WEATHER / "test_nist_ntp_clock_a19b_v2.py"), timeout=30)
    check1 = bool(
        unit.returncode == 0
        and "A19B_NIST_NTP_CLOCK_UNIT_TESTS_PASS 4" in unit.stdout
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

# CHECK 2/3 — adversarial/fail-closed.
if check1:
    adv = run(
        sys.executable,
        str(WEATHER / "test_nist_ntp_clock_a19b_v2_adversarial.py"),
        timeout=30,
    )
    check2 = bool(
        adv.returncode == 0
        and "A19B_NIST_NTP_CLOCK_ADVERSARIAL_TESTS_PASS 8" in adv.stdout
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

# CHECK 3/3 — actual NIST UDP exchange from the WSL clock being evidenced.
if check1 and check2:
    try:
        probe = ntp.probe()
        evidence = probe.get("clock_evidence") or {}
        structurally_valid = bool(
            probe.get("status") == "PROBE_COMPLETE"
            and probe.get("changes_system_clock") is False
            and isinstance(probe.get("samples"), list)
            and len(probe.get("samples")) == len(ntp.NIST_SERVERS)
            and evidence.get("decision") in {
                "CLOCK_EVIDENCE_ELIGIBLE",
                "CLOCK_EVIDENCE_BLOCKED",
            }
            and evidence.get("max_uncertainty_limit_ms")
                == ntp.CLOCK_MAX_UNCERTAINTY_MS
        )
        check3 = structurally_valid
        result["checks"]["check_3_real_nist_probe"] = {
            "pass": check3,
            "probe_status": probe.get("status"),
            "evidence_decision": evidence.get("decision"),
            "evidence_clock_eligible": evidence.get("evidence_clock_eligible"),
            "consensus_absolute_error_bound_ms": evidence.get(
                "consensus_absolute_error_bound_ms"
            ),
            "reasons": evidence.get("reasons"),
            "samples": probe.get("samples"),
        }
    except Exception as exc:
        check3 = False
        probe = {}
        evidence = {}
        result["checks"]["check_3_real_nist_probe"] = {
            "pass": False,
            "detail": f"{type(exc).__name__}: {exc}",
        }
else:
    check3 = False
    probe = {}
    evidence = {}
    result["checks"]["check_3_real_nist_probe"] = {
        "pass": False,
        "status": "SKIPPED_EARLIER_CHECK_FAILED",
    }

local_build_pass = bool(check1 and check2 and check3)
eligible = bool(local_build_pass and evidence.get("evidence_clock_eligible") is True)
result["status"] = "PASS_LOCAL_BUILD" if local_build_pass else "BLOCKED_LOCAL_VALIDATION"
result["clock_evidence"] = evidence
result["evidence_clock_eligible"] = eligible
result["next_gate"] = (
    "NOAA_MADIS_LDM_ACCESS_OR_RUNTIME"
    if eligible
    else "BLOCKED_CLOCK_EVIDENCE"
    if local_build_pass
    else "FIX_NIST_NTP_CLOCK_VALIDATION"
)
result["clock_source_strategy"] = "DIRECT_NIST_UTC_FROM_WSL_CLOCK"
result["provenance"] = {
    "NIST": "public ITS stratum-1 endpoints directly linked to UTC(NIST)",
    "NTP_error_model": "RFC5905 root synchronization distance plus measured path bound",
    "authentication": "anonymous NIST ITS NTP; not cryptographically authenticated",
}

print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if local_build_pass else 1)
