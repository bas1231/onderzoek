#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

ROOT = Path.home() / "prediction_research_weather"
PYTHON = Path.home() / "prediction_research/.venv/bin/python"
BRANCH = "ai/weather-madis-ldm-a19b"
JOB = ROOT / "control/jobs/probe_kernel_clock_a19b_v2.py"


def run(*args: str, timeout: int = 120):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)


def emit(obj: dict, code: int):
    obj.update({"live_trading": False, "paid_action": False, "wallet_action": False, "economic_conclusion": "NO_PROVEN_EDGE"})
    print(json.dumps(obj, indent=2, sort_keys=True))
    raise SystemExit(code)

if not ROOT.is_dir() or not PYTHON.is_file():
    emit({"status": "BLOCKED", "reason": "WEATHER_WORKTREE_OR_VENV_MISSING"}, 2)
branch = run("git", "branch", "--show-current", timeout=20).stdout.strip()
if branch != BRANCH:
    emit({"status": "BLOCKED", "reason": "WRONG_WEATHER_BRANCH", "actual": branch}, 3)
tracked = run("git", "status", "--porcelain", "--untracked-files=no", timeout=20)
if tracked.returncode != 0 or tracked.stdout.strip():
    emit({"status": "BLOCKED", "reason": "WEATHER_WORKTREE_TRACKED_CHANGES", "detail": tracked.stdout[-3000:]}, 4)
pull = run("git", "pull", "--ff-only", "origin", BRANCH, timeout=90)
if pull.returncode != 0:
    emit({"status": "BLOCKED", "reason": "WEATHER_BRANCH_FAST_FORWARD_FAILED", "stderr": pull.stderr[-3000:]}, 5)
if not JOB.is_file():
    emit({"status": "BLOCKED", "reason": "KERNEL_CLOCK_PROBE_JOB_MISSING"}, 6)
cp = run(str(PYTHON), str(JOB.relative_to(ROOT)), timeout=60)
print(cp.stdout, end="")
if cp.stderr:
    print(cp.stderr, end="", file=__import__("sys").stderr)
raise SystemExit(cp.returncode)
