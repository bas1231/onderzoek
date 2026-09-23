#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import py_compile
import subprocess
import sys

ROOT = Path.cwd()
WEATHER = ROOT / "control" / "weather"

FILES = [
    WEATHER / "clock_evidence_sntp_a19c.py",
    WEATHER / "clock_evidence_transport_a19d.py",
    WEATHER / "test_clock_evidence_sntp_a19c.py",
    WEATHER / "test_clock_evidence_transport_a19d.py",
    WEATHER / "test_clock_evidence_sntp_a19c_adversarial.py",
    WEATHER / "test_clock_evidence_transport_a19d_adversarial.py",
]


def run(*args: str, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
    )


def parse_obj(text: str) -> dict:
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


result = {
    "task": "WX-A19D-TRANSPORT-CLOCK-THREE-CHECK",
    "status": "BLOCKED_LOCAL_VALIDATION",
    "local_build_status": "BLOCKED",
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "openai_api": False,
    "checks": {},
}

# CHECK 1/3 — compile + unit/regression.
try:
    for path in FILES:
        py_compile.compile(str(path), doraise=True)

    old_unit = run(sys.executable, str(WEATHER / "test_clock_evidence_sntp_a19c.py"), timeout=60)
    new_unit = run(sys.executable, str(WEATHER / "test_clock_evidence_transport_a19d.py"), timeout=60)
    check1 = bool(
        old_unit.returncode == 0
        and "CLOCK_EVIDENCE_SNTP_A19C_UNIT_TESTS_PASS" in old_unit.stdout
        and new_unit.returncode == 0
        and "CLOCK_EVIDENCE_TRANSPORT_A19D_UNIT_TESTS_PASS" in new_unit.stdout
    )
    result["checks"]["check_1_technical"] = {
        "pass": check1,
        "compile_pass": True,
        "legacy_unit_stdout": old_unit.stdout.strip(),
        "a19d_unit_stdout": new_unit.stdout.strip(),
        "stderr": (old_unit.stderr + "\n" + new_unit.stderr)[-4000:],
    }
except Exception as exc:
    check1 = False
    result["checks"]["check_1_technical"] = {
        "pass": False,
        "compile_pass": False,
        "detail": f"{type(exc).__name__}: {exc}",
    }

# CHECK 2/3 — adversarial/fail closed.
if check1:
    old_adv = run(sys.executable, str(WEATHER / "test_clock_evidence_sntp_a19c_adversarial.py"), timeout=60)
    new_adv = run(sys.executable, str(WEATHER / "test_clock_evidence_transport_a19d_adversarial.py"), timeout=60)
    check2 = bool(
        old_adv.returncode == 0
        and "CLOCK_EVIDENCE_SNTP_A19C_ADVERSARIAL_TESTS_PASS" in old_adv.stdout
        and new_adv.returncode == 0
        and "CLOCK_EVIDENCE_TRANSPORT_A19D_ADVERSARIAL_TESTS_PASS" in new_adv.stdout
    )
    result["checks"]["check_2_fail_closed"] = {
        "pass": check2,
        "legacy_adversarial_stdout": old_adv.stdout.strip(),
        "a19d_adversarial_stdout": new_adv.stdout.strip(),
        "stderr": (old_adv.stderr + "\n" + new_adv.stderr)[-4000:],
    }
else:
    check2 = False
    result["checks"]["check_2_fail_closed"] = {
        "pass": False,
        "status": "SKIPPED_CHECK_1_FAILED",
    }

# CHECK 3/3 — real UDP/123 probe from this exact runtime.
probe_obj: dict = {}
if check1 and check2:
    try:
        probe = run(
            sys.executable,
            str(WEATHER / "clock_evidence_transport_a19d.py"),
            "--rounds",
            "5",
            "--pause-seconds",
            "0.05",
            timeout=90,
        )
        probe_obj = parse_obj(probe.stdout)
        check3 = bool(
            probe.returncode == 0
            and probe_obj.get("schema") == "WEATHER_CLOCK_TRANSPORT_A19D_V1"
            and probe_obj.get("round_count") == 5
            and probe_obj.get("read_only") is True
            and probe_obj.get("clock_adjustment_performed") is False
            and probe_obj.get("live_trading") is False
            and probe_obj.get("paid_action") is False
            and probe_obj.get("wallet_action") is False
        )
        network_observation_count = sum(
            int(row.get("provider_count") or 0)
            for row in (probe_obj.get("rounds") or [])
            if isinstance(row, dict)
        )
        result["checks"]["check_3_real_transport_probe"] = {
            "pass": check3,
            "semantics": "real read-only UDP/123 probe; no system clock adjustment",
            "returncode": probe.returncode,
            "network_observation_count": network_observation_count,
            "round_count": probe_obj.get("round_count"),
            "eligible_round_count": probe_obj.get("eligible_round_count"),
            "clock_offset_ms": probe_obj.get("clock_offset_ms"),
            "clock_uncertainty_ms": probe_obj.get("clock_uncertainty_ms"),
            "clock_total_error_bound_ms": probe_obj.get("clock_total_error_bound_ms"),
            "cross_round_offset_span_ms": probe_obj.get("cross_round_offset_span_ms"),
            "evidence_clock_eligible": probe_obj.get("evidence_clock_eligible"),
            "provider_hosts": probe_obj.get("provider_hosts"),
            "authentication": probe_obj.get("authentication"),
            "network_adversary_resistant": probe_obj.get("network_adversary_resistant"),
            "rounds": probe_obj.get("rounds"),
            "stderr": probe.stderr[-4000:],
        }
    except Exception as exc:
        check3 = False
        network_observation_count = 0
        result["checks"]["check_3_real_transport_probe"] = {
            "pass": False,
            "detail": f"{type(exc).__name__}: {exc}",
        }
else:
    check3 = False
    network_observation_count = 0
    result["checks"]["check_3_real_transport_probe"] = {
        "pass": False,
        "status": "SKIPPED_EARLIER_CHECK_FAILED",
    }

all_local_checks_pass = bool(check1 and check2 and check3)
result["local_build_status"] = "PASS" if all_local_checks_pass else "BLOCKED"

if not all_local_checks_pass:
    result["status"] = "BLOCKED_LOCAL_VALIDATION"
    result["next_gate"] = "FIX_A19D_FAILED_CHECK"
elif network_observation_count == 0:
    result["status"] = "BLOCKED_NTP_TRANSPORT_OR_FIREWALL"
    result["next_gate"] = "VERIFY_UDP_123_OR_ALTERNATE_READ_ONLY_TIME_TRANSPORT"
elif probe_obj.get("evidence_clock_eligible") is not True:
    result["status"] = "BLOCKED_REAL_CLOCK_EVIDENCE"
    result["next_gate"] = "CLOCK_EVIDENCE_TRANSPORT_OR_SYSTEM_SYNC"
else:
    result["status"] = "PASS_REAL_CLOCK_EVIDENCE"
    result["next_gate"] = "A19B_V2_QUEUE_NATIVE_WITH_TRANSPORT_CLOCK_EVIDENCE"

result["clock_evidence"] = {
    "evidence_clock_eligible": bool(probe_obj.get("evidence_clock_eligible") is True),
    "clock_offset_ms": probe_obj.get("clock_offset_ms"),
    "clock_uncertainty_ms": probe_obj.get("clock_uncertainty_ms"),
    "clock_total_error_bound_ms": probe_obj.get("clock_total_error_bound_ms"),
    "round_count": probe_obj.get("round_count"),
    "eligible_round_count": probe_obj.get("eligible_round_count"),
    "ordinary_ntp_authentication": "none",
}

print(json.dumps(result, indent=2, sort_keys=True))
# Local build validation failure is a process failure. A real-world evidence
# block is a successful research outcome and therefore exits 0.
raise SystemExit(0 if all_local_checks_pass else 1)
