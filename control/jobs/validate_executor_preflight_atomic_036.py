#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import py_compile
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "control" / "executor_preflight.py"
TEST = ROOT / "tests" / "bridge" / "test_executor_preflight_atomic_support.py"


def run_pytest(expr: str) -> dict:
    cp = subprocess.run(
        [sys.executable, "-m", "pytest", str(TEST), "-q", "-k", expr],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=120,
    )
    return {
        "pass": cp.returncode == 0,
        "returncode": cp.returncode,
        "stdout": cp.stdout[-8000:],
        "stderr": cp.stderr[-4000:],
    }


result = {
    "task": "CONTROL-ATOMIC-TASK-PREREQ-036",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "openai_api": False,
    "economic_conclusion": "NO_PROVEN_EDGE",
    "checks": {},
}

try:
    py_compile.compile(str(TARGET), doraise=True)
    py_compile.compile(str(TEST), doraise=True)
    c1 = run_pytest("same_commit_task_and_script_pass")
    c1["compile_pass"] = True
except Exception as exc:
    c1 = {
        "pass": False,
        "compile_pass": False,
        "detail": f"{type(exc).__name__}: {exc}",
    }
result["checks"]["check_1_technical"] = c1

if c1.get("pass"):
    c2 = run_pytest("later_added_script_does_not_rescue_old_task or script_change_after_task_commit_fails_closed")
else:
    c2 = {"pass": False, "status": "SKIPPED_CHECK_1_FAILED"}
result["checks"]["check_2_fail_closed"] = c2

if c1.get("pass") and c2.get("pass"):
    c3 = run_pytest("unchanged_task_and_script_can_run_from_descendant_head")
else:
    c3 = {"pass": False, "status": "SKIPPED_EARLIER_CHECK_FAILED"}
result["checks"]["check_3_realistic_provenance_replay"] = c3

all_pass = bool(c1.get("pass") and c2.get("pass") and c3.get("pass"))
result["status"] = "PASS" if all_pass else "BLOCKED"
result["next_gate"] = "RETURN_TO_WEATHER_A19C" if all_pass else "FIX_CONTROL_PREFLIGHT"
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if all_pass else 1)
