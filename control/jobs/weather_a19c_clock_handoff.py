#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path.home() / "prediction_research_weather"
PYTHON = Path.home() / "prediction_research/.venv/bin/python"
BRANCH = "ai/weather-madis-ldm-a19b"
JOB = ROOT / "control/jobs/validate_weather_a19c_clock.py"


def run(*args: str, timeout: int = 1200):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)


if not ROOT.is_dir():
    print("WEATHER_WORKTREE_MISSING")
    raise SystemExit(2)
if not PYTHON.is_file():
    print("PREDICTION_VENV_PYTHON_MISSING")
    raise SystemExit(3)

branch = run("git", "branch", "--show-current", timeout=30).stdout.strip()
if branch != BRANCH:
    print(f"WRONG_WEATHER_BRANCH expected={BRANCH} actual={branch}")
    raise SystemExit(4)

tracked = run("git", "status", "--porcelain", "--untracked-files=no", timeout=30)
if tracked.returncode != 0 or tracked.stdout.strip():
    print("WEATHER_WORKTREE_TRACKED_CHANGES")
    print(tracked.stdout[-4000:] or tracked.stderr[-4000:])
    raise SystemExit(5)

pull = run("git", "pull", "--ff-only", "origin", BRANCH, timeout=120)
if pull.returncode != 0:
    print("WEATHER_BRANCH_FAST_FORWARD_FAILED")
    print(pull.stdout[-4000:])
    print(pull.stderr[-4000:], file=sys.stderr)
    raise SystemExit(6)

if not JOB.is_file():
    print("A19C_VALIDATOR_MISSING_AFTER_FAST_FORWARD")
    raise SystemExit(7)

proc = run(str(PYTHON), str(JOB.relative_to(ROOT)), timeout=300)
print(proc.stdout, end="")
if proc.stderr:
    print(proc.stderr, file=sys.stderr, end="")
raise SystemExit(proc.returncode)
