#!/usr/bin/env python3
"""A19C three-gate validation for clock evidence.

CHECK 1/3 technical: compile + deterministic unit/regression tests for both
kernel discipline evidence and independent SNTP consensus evidence.
CHECK 2/3 adversarial/fail-closed tests for both paths.
CHECK 3/3 realistic/prospective: execute both read-only probes on this host.

A technically correct probe can still end in BLOCKED_CLOCK_EVIDENCE. Evidence
eligibility is a research gate, not the same thing as software validation.
No system clock is changed. No package is installed. No paid service/API,
wallet action, or trading occurs.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import py_compile
import subprocess
import sys

ROOT = Path.cwd()
WEATHER = ROOT / "control" / "weather"
EVIDENCE = ROOT / "evidence" / "weather"
EVIDENCE.mkdir(parents=True, exist_ok=True)

KERNEL_MODULE = WEATHER / "clock_evidence_a19c.py"
SNTP_MODULE = WEATHER / "clock_evidence_sntp_a19c.py"
KERNEL_UNIT = WEATHER / "test_clock_evidence_a19c.py"
SNTP_UNIT = WEATHER / "test_clock_evidence_sntp_a19c.py"
KERNEL_ADV = WEATHER / "test_clock_evidence_a19c_adversarial.py"
SNTP_ADV = WEATHER / "test_clock_evidence_sntp_a19c_adversarial.py"
WRAPPER = WEATHER / "madis_ldm_queue_native_a19b_v2_clocked.py"


def run(*args: str, timeout: int = 90) -> dict:
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
            "stderr": (exc.stderr or "")[-10000:] if isinstance(exc.stderr, str) else "",
            "timed_out": True,
        }


def parse_obj(text: str) -> dict:
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def test_run(path: Path, marker: str) -> dict:
    item = run(sys.executable, str(path), timeout=60)
    item["required_marker"] = marker
    item["pass"] = item["returncode"] == 0 and marker in item["stdout"]
    return item


result = {
    "task": "WEATHER-CLOCK-EVIDENCE-A19C-THREE-CHECK",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "openai_api": False,
    "clock_adjustment": False,
    "package_installation": False,
    "economic_conclusion": "NO_PROVEN_EDGE",
    "checks": {},
}

# CHECK 1/3 — technical.
compile_errors: list[str] = []
for path in (
    KERNEL_MODULE, SNTP_MODULE, KERNEL_UNIT, SNTP_UNIT,
    KERNEL_ADV, SNTP_ADV, WRAPPER,
):
    try:
        py_compile.compile(str(path), doraise=True)
    except Exception as exc:
        compile_errors.append(f"{path}: {type(exc).__name__}: {exc}")

unit_runs: list[dict] = []
if not compile_errors:
    unit_runs = [
        test_run(KERNEL_UNIT, "CLOCK_EVIDENCE_A19C_UNIT_TESTS_PASS"),
        test_run(SNTP_UNIT, "CLOCK_EVIDENCE_SNTP_A19C_UNIT_TESTS_PASS"),
    ]
check1 = bool(not compile_errors and all(item["pass"] for item in unit_runs))
result["checks"]["check_1_technical"] = {
    "pass": check1,
    "compile_pass": not compile_errors,
    "compile_errors": compile_errors,
    "unit_runs": unit_runs,
}

# CHECK 2/3 — adversarial/fail-closed.
adversarial_runs: list[dict] = []
if check1:
    adversarial_runs = [
        test_run(KERNEL_ADV, "CLOCK_EVIDENCE_A19C_ADVERSARIAL_TESTS_PASS"),
        test_run(SNTP_ADV, "CLOCK_EVIDENCE_SNTP_A19C_ADVERSARIAL_TESTS_PASS"),
    ]
check2 = bool(check1 and all(item["pass"] for item in adversarial_runs))
result["checks"]["check_2_fail_closed"] = {
    "pass": check2,
    "status": "RUN" if check1 else "SKIPPED_CHECK_1_FAILED",
    "runs": adversarial_runs,
}

# CHECK 3/3 — real read-only probe chain. A structured fail-closed outcome is
# a technically successful end-to-end probe. Eligibility is evaluated below.
kernel_run: dict = {}
sntp_run: dict = {}
kernel: dict = {}
sntp: dict = {}
if check1 and check2:
    kernel_run = run(sys.executable, str(KERNEL_MODULE), timeout=30)
    sntp_run = run(sys.executable, str(SNTP_MODULE), timeout=20)
    kernel = parse_obj(kernel_run.get("stdout", ""))
    sntp = parse_obj(sntp_run.get("stdout", ""))

kernel_structured = bool(
    kernel_run.get("returncode") == 0
    and kernel.get("clock_source") == "linux-kernel-adjtimex+ntp_gettime"
    and kernel.get("read_only") is True
    and "evidence_clock_eligible" in kernel
)
sntp_structured = bool(
    sntp_run.get("returncode") == 0
    and sntp.get("clock_source") == "sntp_consensus"
    and int(sntp.get("required_distinct_servers") or 0) == 3
    and "evidence_clock_eligible" in sntp
)
check3 = bool(check1 and check2 and kernel_structured and sntp_structured)
result["checks"]["check_3_real_probe"] = {
    "pass": check3,
    "status": "RUN" if check1 and check2 else "SKIPPED_EARLIER_CHECK_FAILED",
    "kernel_structured": kernel_structured,
    "sntp_structured": sntp_structured,
    "kernel": kernel,
    "sntp": sntp,
    "kernel_runner": kernel_run,
    "sntp_runner": sntp_run,
    "semantics": "real read-only evidence probes; system clock not modified",
}

all_checks_pass = bool(check1 and check2 and check3)
kernel_eligible = kernel.get("evidence_clock_eligible") is True
sntp_eligible = sntp.get("evidence_clock_eligible") is True
clock_eligible = bool(all_checks_pass and kernel_eligible and sntp_eligible)

if not all_checks_pass:
    status = "BLOCKED_LOCAL_VALIDATION"
    next_gate = "FIX_A19C_FAILED_CHECK"
    exit_code = 1
elif not clock_eligible:
    status = "PASS_LOCAL_BUILD"
    next_gate = "BLOCKED_CLOCK_EVIDENCE"
    exit_code = 0
else:
    status = "PASS_CLOCK_EVIDENCE"
    next_gate = "NOAA_MADIS_LDM_ACCESS_AND_QUEUE_NATIVE_CAPTURE"
    exit_code = 0

result.update({
    "status": status,
    "local_build_status": "PASS" if all_checks_pass else "FAILED",
    "clock_evidence_eligible": clock_eligible,
    "kernel_clock_eligible": kernel_eligible,
    "sntp_clock_eligible": sntp_eligible,
    "next_gate": next_gate,
    "terminal_for_current_authorization": next_gate == "BLOCKED_CLOCK_EVIDENCE",
})

out = EVIDENCE / "A19C_CLOCK_EVIDENCE-latest.json"
out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
result["evidence_path"] = str(out)
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(exit_code)
