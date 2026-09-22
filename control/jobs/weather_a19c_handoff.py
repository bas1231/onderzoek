#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

ROOT = Path.home() / "prediction_research_weather"
PYTHON = Path.home() / "prediction_research/.venv/bin/python"
BRANCH = "ai/weather-madis-ldm-a19b"
VALIDATOR = ROOT / "control/jobs/validate_clock_evidence_a19c.py"


def run(*args: str, timeout: int = 600):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)


def parse(text: str) -> dict:
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def finish(payload: dict, code: int = 0):
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
    finish({"status": "BLOCKED", "next_gate": "WEATHER_WORKTREE_MISSING"}, 2)
if not PYTHON.is_file():
    finish({"status": "BLOCKED", "next_gate": "PREDICTION_VENV_PYTHON_MISSING"}, 3)

branch = run("git", "branch", "--show-current", timeout=30).stdout.strip()
if branch != BRANCH:
    finish({
        "status": "BLOCKED",
        "next_gate": "WRONG_WEATHER_BRANCH",
        "expected_branch": BRANCH,
        "actual_branch": branch,
    }, 4)

# Never overwrite another session's tracked Weather changes.
tracked = run("git", "status", "--porcelain", "--untracked-files=no", timeout=30)
if tracked.returncode != 0 or tracked.stdout.strip():
    finish({
        "status": "BLOCKED",
        "next_gate": "WEATHER_WORKTREE_TRACKED_CHANGES",
        "detail": tracked.stdout[-4000:] or tracked.stderr[-4000:],
    }, 5)

# Update only the isolated Weather branch, fast-forward only.
pull = run("git", "pull", "--ff-only", "origin", BRANCH, timeout=120)
if pull.returncode != 0:
    finish({
        "status": "BLOCKED",
        "next_gate": "WEATHER_BRANCH_FAST_FORWARD_FAILED",
        "stdout": pull.stdout[-4000:],
        "stderr": pull.stderr[-4000:],
    }, 6)

head = run("git", "rev-parse", "HEAD", timeout=30).stdout.strip()
if not VALIDATOR.is_file():
    finish({
        "status": "BLOCKED_LOCAL_BUILD",
        "weather_head": head,
        "next_gate": "A19C_UNIFIED_VALIDATOR_MISSING",
    }, 7)

probe = run(str(PYTHON), str(VALIDATOR.relative_to(ROOT)), timeout=180)
obj = parse(probe.stdout)
step = {
    "returncode": probe.returncode,
    "status": obj.get("status"),
    "local_build_status": obj.get("local_build_status"),
    "checks": obj.get("checks"),
    "clock_evidence_eligible": obj.get("clock_evidence_eligible"),
    "kernel_clock_eligible": obj.get("kernel_clock_eligible"),
    "sntp_clock_eligible": obj.get("sntp_clock_eligible"),
    "next_gate": obj.get("next_gate"),
    "evidence_path": obj.get("evidence_path"),
    "stderr": probe.stderr[-5000:],
}

if probe.returncode != 0 or obj.get("local_build_status") != "PASS":
    finish({
        "status": "BLOCKED_LOCAL_VALIDATION",
        "weather_head": head,
        "steps": {"a19c_clock_evidence": step},
        "next_gate": obj.get("next_gate") or "FIX_A19C_FAILED_CHECK",
        "terminal_for_current_authorization": False,
    }, 8)

next_gate = str(obj.get("next_gate") or "UNKNOWN_A19C_GATE")
finish({
    "status": "COMPLETED_A19C_CLOCK_GATE",
    "weather_head": head,
    "steps": {"a19c_clock_evidence": step},
    "clock_evidence_eligible": obj.get("clock_evidence_eligible") is True,
    "next_gate": next_gate,
    "terminal_for_current_authorization": next_gate == "BLOCKED_CLOCK_EVIDENCE",
}, 0)
