#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

ROOT = Path.home() / "prediction_research_weather"
PYTHON = Path.home() / "prediction_research/.venv/bin/python"
BRANCH = "ai/weather-madis-ldm-a19b"
VALIDATOR = ROOT / "control/jobs/validate_madis_ldm_a19b_v2.py"


def run(*args: str, timeout: int = 1200) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
    )


def parse_obj(text: str) -> dict:
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def finish(payload: dict, code: int) -> None:
    payload.update({
        "task": "WX-A19B-V2-CLOCK-DIAGNOSTIC",
        "economic_conclusion": "NO_PROVEN_EDGE",
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
        "system_changes_performed": False,
    })
    print(json.dumps(payload, indent=2, sort_keys=True))
    raise SystemExit(code)


if not ROOT.is_dir():
    finish({"status": "DIAGNOSTIC_FAILED", "next_gate": "WEATHER_WORKTREE_MISSING"}, 2)
if not PYTHON.is_file():
    finish({"status": "DIAGNOSTIC_FAILED", "next_gate": "PREDICTION_VENV_PYTHON_MISSING"}, 3)

branch = run("git", "branch", "--show-current", timeout=30).stdout.strip()
if branch != BRANCH:
    finish({
        "status": "DIAGNOSTIC_FAILED",
        "next_gate": "WRONG_WEATHER_BRANCH",
        "expected_branch": BRANCH,
        "actual_branch": branch,
    }, 4)

tracked = run("git", "status", "--porcelain", "--untracked-files=no", timeout=30)
if tracked.returncode != 0 or tracked.stdout.strip():
    finish({
        "status": "DIAGNOSTIC_FAILED",
        "next_gate": "WEATHER_WORKTREE_TRACKED_CHANGES",
        "detail": tracked.stdout[-4000:] or tracked.stderr[-4000:],
    }, 5)

pull = run("git", "pull", "--ff-only", "origin", BRANCH, timeout=120)
if pull.returncode != 0:
    finish({
        "status": "DIAGNOSTIC_FAILED",
        "next_gate": "WEATHER_BRANCH_FAST_FORWARD_FAILED",
        "stdout": pull.stdout[-4000:],
        "stderr": pull.stderr[-4000:],
    }, 6)

head = run("git", "rev-parse", "HEAD", timeout=30).stdout.strip()
if not VALIDATOR.is_file():
    finish({
        "status": "DIAGNOSTIC_FAILED",
        "weather_head": head,
        "next_gate": "A19B_V2_VALIDATOR_MISSING",
    }, 7)

validation = run(str(PYTHON), str(VALIDATOR.relative_to(ROOT)), timeout=1200)
obj = parse_obj(validation.stdout)
local_build_pass = bool(
    validation.returncode == 0
    and obj.get("status") == "PASS_LOCAL_BUILD"
)

payload = {
    "status": "COMPLETED_DIAGNOSTIC" if local_build_pass else "LOCAL_VALIDATION_FAILED",
    "weather_head": head,
    "validator_returncode": validation.returncode,
    "validator_status": obj.get("status"),
    "checks": obj.get("checks"),
    "clock_readiness": obj.get("clock_readiness"),
    "ldm_runtime_inventory": obj.get("ldm_runtime_inventory"),
    "queue_insertion_evidence_state": obj.get("queue_insertion_evidence_state"),
    "next_gate": obj.get("next_gate") or "UNKNOWN_A19B_V2_GATE",
    "validator_stderr": validation.stderr[-5000:],
}

# A scientifically blocked clock/runtime gate is a successful diagnostic.
# Only an actual local build/validator failure gets a non-zero process status.
finish(payload, 0 if local_build_pass else 10)
