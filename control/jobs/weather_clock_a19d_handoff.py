#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

ROOT = Path.home() / "prediction_research_weather"
PYTHON = Path.home() / "prediction_research/.venv/bin/python"
BRANCH = "ai/weather-madis-ldm-a19b"
JOB = ROOT / "control/jobs/validate_clock_transport_a19d.py"


def run(*args: str, timeout: int = 180):
    return subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
    )


def emit(payload: dict, code: int) -> None:
    payload.update({
        "economic_conclusion": "NO_PROVEN_EDGE",
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
        "openai_api": False,
    })
    print(json.dumps(payload, indent=2, sort_keys=True))
    raise SystemExit(code)


if not ROOT.is_dir():
    emit({"status": "BLOCKED", "next_gate": "WEATHER_WORKTREE_MISSING"}, 2)
if not PYTHON.is_file():
    emit({"status": "BLOCKED", "next_gate": "PREDICTION_VENV_PYTHON_MISSING"}, 3)

branch = run("git", "branch", "--show-current", timeout=30).stdout.strip()
if branch != BRANCH:
    emit({
        "status": "BLOCKED",
        "next_gate": "WRONG_WEATHER_BRANCH",
        "expected_branch": BRANCH,
        "actual_branch": branch,
    }, 4)

tracked = run("git", "status", "--porcelain", "--untracked-files=no", timeout=30)
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
        "stdout": pull.stdout[-4000:],
        "stderr": pull.stderr[-4000:],
    }, 6)

head = run("git", "rev-parse", "HEAD", timeout=30).stdout.strip()
if not JOB.is_file():
    emit({
        "status": "BLOCKED",
        "weather_head": head,
        "next_gate": "A19D_VALIDATOR_MISSING_AFTER_FAST_FORWARD",
    }, 7)

proc = subprocess.run(
    [str(PYTHON), str(JOB.relative_to(ROOT))],
    cwd=ROOT,
    text=True,
    capture_output=True,
    timeout=180,
)

try:
    parsed = json.loads(proc.stdout)
except Exception:
    parsed = {}

out = {
    "status": parsed.get("status") or ("FAILED" if proc.returncode else "COMPLETED"),
    "weather_head": head,
    "validator_returncode": proc.returncode,
    "local_build_status": parsed.get("local_build_status"),
    "next_gate": parsed.get("next_gate"),
    "clock_evidence": parsed.get("clock_evidence"),
    "checks": parsed.get("checks"),
    "validator_stdout": proc.stdout[-30000:],
    "validator_stderr": proc.stderr[-6000:],
}

# A real-world clock/transport block is an expected research result and the
# validator returns zero. Only local validation/process failures are failures.
emit(out, proc.returncode)
