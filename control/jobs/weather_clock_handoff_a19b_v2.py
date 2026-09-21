#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

ROOT = Path.home() / "prediction_research_weather"
PY = Path.home() / "prediction_research/.venv/bin/python"
BRANCH = "ai/weather-madis-ldm-a19b"
JOB = ROOT / "control/jobs/validate_kernel_clock_a19b_v2.py"
ALLOWED_NEXT_GATES = {
    "BLOCKED_CLOCK_EVIDENCE",
    "BLOCKED_NOAA_MADIS_LDM_ACCESS_OR_RUNTIME",
}


def run(*args: str, timeout: int = 120):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)


def emit(obj: dict, code: int = 0):
    obj.update({
        "economic_conclusion": "NO_PROVEN_EDGE",
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
        "openai_api": False,
    })
    print(json.dumps(obj, indent=2, sort_keys=True))
    raise SystemExit(code)


def parse_validator(text: str) -> dict:
    try:
        obj = json.loads(text)
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


if not ROOT.is_dir():
    emit({"status": "BLOCKED", "next_gate": "WEATHER_WORKTREE_MISSING"}, 2)
if not PY.is_file():
    emit({"status": "BLOCKED", "next_gate": "PREDICTION_VENV_PYTHON_MISSING"}, 3)

branch = run("git", "branch", "--show-current", timeout=20)
actual_branch = branch.stdout.strip() if branch.returncode == 0 else ""
if branch.returncode != 0 or actual_branch != BRANCH:
    emit({
        "status": "BLOCKED",
        "next_gate": "WRONG_WEATHER_BRANCH",
        "expected_branch": BRANCH,
        "actual_branch": actual_branch,
        "stderr": branch.stderr[-3000:],
    }, 4)

tracked = run("git", "status", "--porcelain", "--untracked-files=no", timeout=20)
if tracked.returncode != 0 or tracked.stdout.strip():
    emit({
        "status": "BLOCKED",
        "next_gate": "WEATHER_WORKTREE_TRACKED_CHANGES",
        "detail": tracked.stdout[-4000:] or tracked.stderr[-4000:],
    }, 5)

pull = run("git", "pull", "--ff-only", "origin", BRANCH, timeout=120)
if pull.returncode != 0:
    emit({
        "status": "BLOCKED",
        "next_gate": "WEATHER_BRANCH_FAST_FORWARD_FAILED",
        "stdout": pull.stdout[-3000:],
        "stderr": pull.stderr[-3000:],
    }, 6)

head = run("git", "rev-parse", "HEAD", timeout=20)
weather_head = head.stdout.strip() if head.returncode == 0 else None
if not JOB.is_file():
    emit({
        "status": "BLOCKED",
        "next_gate": "CLOCK_VALIDATOR_MISSING",
        "weather_head": weather_head,
    }, 7)

try:
    cp = run(str(PY), str(JOB.relative_to(ROOT)), timeout=180)
except subprocess.TimeoutExpired as exc:
    emit({
        "status": "BLOCKED_CLOCK_VALIDATION",
        "next_gate": "CLOCK_VALIDATOR_TIMEOUT",
        "weather_head": weather_head,
        "stdout": (exc.stdout or "")[-5000:] if isinstance(exc.stdout, str) else "",
        "stderr": (exc.stderr or "")[-3000:] if isinstance(exc.stderr, str) else "",
    }, 124)

obj = parse_validator(cp.stdout)
if not obj:
    emit({
        "status": "BLOCKED_CLOCK_VALIDATION",
        "next_gate": "CLOCK_VALIDATOR_MALFORMED_OUTPUT",
        "weather_head": weather_head,
        "validator_returncode": cp.returncode,
        "stdout": cp.stdout[-5000:],
        "stderr": cp.stderr[-3000:],
    }, 8)

if cp.returncode != 0 or obj.get("status") != "PASS_LOCAL_BUILD":
    emit({
        "status": "BLOCKED_CLOCK_VALIDATION",
        "next_gate": obj.get("next_gate") or "FIX_KERNEL_CLOCK_VALIDATION",
        "weather_head": weather_head,
        "validator_returncode": cp.returncode,
        "validator": obj,
        "stderr": cp.stderr[-3000:],
    }, 9)

next_gate = str(obj.get("next_gate") or "")
if next_gate not in ALLOWED_NEXT_GATES:
    emit({
        "status": "BLOCKED_CLOCK_VALIDATION",
        "next_gate": "UNRECOGNIZED_CLOCK_NEXT_GATE",
        "reported_next_gate": next_gate,
        "weather_head": weather_head,
        "validator": obj,
    }, 10)

emit({
    "status": "COMPLETED_CLOCK_GATE",
    "validator": obj,
    "next_gate": next_gate,
    "weather_head": weather_head,
    "terminal_for_current_authorization": True,
}, 0)
