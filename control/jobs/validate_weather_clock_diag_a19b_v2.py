#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import py_compile
import subprocess
import sys

ROOT = Path.cwd()
TARGET = ROOT / "control/jobs/weather_clock_diag_a19b_v2.py"


def run(*args: str, env: dict[str, str] | None = None, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        env=env,
    )


def parse_obj(text: str) -> dict:
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


result = {
    "task": "WEATHER-A19B-V2-CLOCK-DIAGNOSTIC-THREE-CHECK",
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "checks": {},
}

# CHECK 1/3 — technical compile + required safety markers.
try:
    py_compile.compile(str(TARGET), doraise=True)
    source = TARGET.read_text(encoding="utf-8")
    required = [
        '"system_modified": False',
        '"live_trading": False',
        '"paid_action": False',
        '"wallet_action": False',
        '"BLOCKED_CLOCK_EVIDENCE"',
        'raise SystemExit(0)',
    ]
    missing = [marker for marker in required if marker not in source]
    check1 = not missing
    result["checks"]["check_1_technical"] = {
        "pass": check1,
        "compile_pass": True,
        "missing_required_markers": missing,
    }
except Exception as exc:
    check1 = False
    result["checks"]["check_1_technical"] = {
        "pass": False,
        "compile_pass": False,
        "detail": f"{type(exc).__name__}: {exc}",
    }

# CHECK 2/3 — fail closed when normal timing utilities are undiscoverable.
if check1:
    env = dict(os.environ)
    env["PATH"] = ""
    cp = run(sys.executable, str(TARGET.relative_to(ROOT)), env=env)
    obj = parse_obj(cp.stdout)
    check2 = bool(
        cp.returncode == 0
        and obj.get("status") == "DIAGNOSTIC_COMPLETED"
        and obj.get("research_gate") == "BLOCKED_CLOCK_EVIDENCE"
        and obj.get("evidence_clock_eligible") is False
        and obj.get("system_modified") is False
        and obj.get("live_trading") is False
        and obj.get("paid_action") is False
        and obj.get("wallet_action") is False
    )
    result["checks"]["check_2_fail_closed"] = {
        "pass": check2,
        "returncode": cp.returncode,
        "research_gate": obj.get("research_gate"),
        "evidence_clock_eligible": obj.get("evidence_clock_eligible"),
        "system_modified": obj.get("system_modified"),
        "stderr": cp.stderr[-2000:],
    }
else:
    check2 = False
    result["checks"]["check_2_fail_closed"] = {
        "pass": False,
        "status": "SKIPPED_CHECK_1_FAILED",
    }

# CHECK 3/3 — real passive run on this host.
if check1 and check2:
    cp = run(sys.executable, str(TARGET.relative_to(ROOT)))
    obj = parse_obj(cp.stdout)
    allowed_gates = {"CLOCK_EVIDENCE_READY", "BLOCKED_CLOCK_EVIDENCE"}
    check3 = bool(
        cp.returncode == 0
        and obj.get("status") == "DIAGNOSTIC_COMPLETED"
        and obj.get("research_gate") in allowed_gates
        and obj.get("system_modified") is False
        and obj.get("live_trading") is False
        and obj.get("paid_action") is False
        and obj.get("wallet_action") is False
        and obj.get("economic_conclusion") == "NO_PROVEN_EDGE"
    )
    result["checks"]["check_3_real_host"] = {
        "pass": check3,
        "returncode": cp.returncode,
        "research_gate": obj.get("research_gate"),
        "evidence_clock_eligible": obj.get("evidence_clock_eligible"),
        "clock_health": obj.get("clock_health"),
        "inventory": obj.get("inventory"),
        "system_modified": obj.get("system_modified"),
        "stderr": cp.stderr[-2000:],
    }
else:
    check3 = False
    obj = {}
    result["checks"]["check_3_real_host"] = {
        "pass": False,
        "status": "SKIPPED_EARLIER_CHECK_FAILED",
    }

all_pass = bool(check1 and check2 and check3)
result["status"] = "PASS" if all_pass else "BLOCKED_LOCAL_VALIDATION"
result["research_gate"] = obj.get("research_gate") if all_pass else "FIX_CLOCK_DIAGNOSTIC_VALIDATION"
result["evidence_clock_eligible"] = obj.get("evidence_clock_eligible") if all_pass else False
result["terminal_for_current_authorization"] = bool(
    all_pass and obj.get("research_gate") == "BLOCKED_CLOCK_EVIDENCE"
)
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if all_pass else 1)
