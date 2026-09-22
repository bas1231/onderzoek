#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import subprocess

ROOT = Path.home() / "prediction_research_weather"
PYTHON = Path.home() / "prediction_research/.venv/bin/python"
BRANCH = "ai/weather-madis-ldm-a19b"
JOB = ROOT / "control/jobs/validate_weather_clock_diag_a19b_v2.py"


def run(*args: str, timeout: int = 300):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)


if not ROOT.is_dir():
    print('{"status":"BLOCKED","next_gate":"WEATHER_WORKTREE_MISSING","economic_conclusion":"NO_PROVEN_EDGE"}')
    raise SystemExit(2)
if not PYTHON.is_file():
    print('{"status":"BLOCKED","next_gate":"PREDICTION_VENV_PYTHON_MISSING","economic_conclusion":"NO_PROVEN_EDGE"}')
    raise SystemExit(3)

branch = run("git", "branch", "--show-current", timeout=30).stdout.strip()
if branch != BRANCH:
    print('{"status":"BLOCKED","next_gate":"WRONG_WEATHER_BRANCH","economic_conclusion":"NO_PROVEN_EDGE"}')
    raise SystemExit(4)

tracked = run("git", "status", "--porcelain", "--untracked-files=no", timeout=30)
if tracked.returncode != 0 or tracked.stdout.strip():
    print('{"status":"BLOCKED","next_gate":"WEATHER_WORKTREE_TRACKED_CHANGES","economic_conclusion":"NO_PROVEN_EDGE"}')
    raise SystemExit(5)

pull = run("git", "pull", "--ff-only", "origin", BRANCH, timeout=120)
if pull.returncode != 0:
    print(pull.stdout, end="")
    print(pull.stderr, end="")
    raise SystemExit(6)

if not JOB.is_file():
    print('{"status":"BLOCKED","next_gate":"CLOCK_DIAGNOSTIC_JOB_MISSING_AFTER_FAST_FORWARD","economic_conclusion":"NO_PROVEN_EDGE"}')
    raise SystemExit(7)

proc = subprocess.run(
    [str(PYTHON), str(JOB.relative_to(ROOT))],
    cwd=ROOT,
    text=True,
    capture_output=True,
    timeout=300,
)
print(proc.stdout, end="")
if proc.stderr:
    print(proc.stderr, end="", file=__import__("sys").stderr)
raise SystemExit(proc.returncode)
