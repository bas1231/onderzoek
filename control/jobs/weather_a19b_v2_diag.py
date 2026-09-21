#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

ROOT = Path.home() / "prediction_research_weather"
PYTHON = Path.home() / "prediction_research/.venv/bin/python"
BRANCH = "ai/weather-madis-ldm-a19b"
JOB = ROOT / "control/jobs/validate_madis_ldm_a19b_v2.py"


def run(*args: str, timeout: int = 1200):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)


def emit(payload: dict, code: int = 0):
    payload.update({
        "economic_conclusion": "NO_PROVEN_EDGE",
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
    })
    print(json.dumps(payload, indent=2, sort_keys=True))
    raise SystemExit(code)


if not ROOT.is_dir():
    emit({"status": "BLOCKED", "reason": "WEATHER_WORKTREE_MISSING"}, 2)
if not PYTHON.is_file():
    emit({"status": "BLOCKED", "reason": "PREDICTION_VENV_PYTHON_MISSING"}, 3)

branch = run("git", "branch", "--show-current", timeout=30).stdout.strip()
if branch != BRANCH:
    emit({"status": "BLOCKED", "reason": "WRONG_WEATHER_BRANCH", "actual": branch}, 4)

tracked = run("git", "status", "--porcelain", "--untracked-files=no", timeout=30)
if tracked.returncode != 0:
    emit({"status": "BLOCKED", "reason": "GIT_STATUS_FAILED", "stderr": tracked.stderr[-4000:]}, 5)
if tracked.stdout.strip():
    emit({"status": "BLOCKED", "reason": "WEATHER_WORKTREE_TRACKED_CHANGES", "detail": tracked.stdout[-8000:]}, 6)

pull = run("git", "pull", "--ff-only", "origin", BRANCH, timeout=120)
if pull.returncode != 0:
    emit({"status": "BLOCKED", "reason": "WEATHER_BRANCH_FAST_FORWARD_FAILED", "stdout": pull.stdout[-8000:], "stderr": pull.stderr[-8000:]}, 7)

head = run("git", "rev-parse", "HEAD", timeout=30).stdout.strip()
if not JOB.is_file():
    emit({"status": "BLOCKED", "reason": "A19B_V2_VALIDATOR_MISSING", "weather_head": head}, 8)

proc = run(str(PYTHON), str(JOB.relative_to(ROOT)), timeout=1200)
try:
    parsed = json.loads(proc.stdout)
except Exception:
    parsed = None

emit({
    "status": "PASS" if proc.returncode == 0 else "FAILED",
    "weather_head": head,
    "validator_returncode": proc.returncode,
    "validator_parsed": parsed,
    "validator_stdout": proc.stdout[-30000:],
    "validator_stderr": proc.stderr[-12000:],
}, proc.returncode)
