#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

ROOT = Path.home() / "prediction_research_weather"
PYTHON = Path.home() / "prediction_research/.venv/bin/python"
BRANCH = "ai/weather-madis-ldm-a19b"
JOB = ROOT / "control/jobs/validate_clock_evidence_kernel_a19c.py"


def run(*args: str, timeout: int = 300):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)


def emit(payload: dict, code: int = 0):
    payload.update({
        "economic_conclusion": "NO_PROVEN_EDGE",
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
        "openai_api": False,
    })
    print(json.dumps(payload, indent=2, sort_keys=True))
    raise SystemExit(code)


if not ROOT.is_dir() or not PYTHON.is_file():
    emit({"status": "BLOCKED_TRANSPORT", "next_gate": "LOCAL_WEATHER_RUNTIME_MISSING"}, 2)

branch = run("git", "branch", "--show-current", timeout=30).stdout.strip()
if branch != BRANCH:
    emit({
        "status": "BLOCKED_TRANSPORT",
        "next_gate": "WRONG_WEATHER_BRANCH",
        "expected": BRANCH,
        "actual": branch,
    }, 3)

tracked = run("git", "status", "--porcelain", "--untracked-files=no", timeout=30)
if tracked.returncode != 0 or tracked.stdout.strip():
    emit({
        "status": "BLOCKED_TRANSPORT",
        "next_gate": "WEATHER_WORKTREE_TRACKED_CHANGES",
        "detail": tracked.stdout[-4000:] or tracked.stderr[-4000:],
    }, 4)

pull = run("git", "pull", "--ff-only", "origin", BRANCH, timeout=120)
if pull.returncode != 0:
    emit({
        "status": "BLOCKED_TRANSPORT",
        "next_gate": "WEATHER_BRANCH_FAST_FORWARD_FAILED",
        "stdout": pull.stdout[-4000:],
        "stderr": pull.stderr[-4000:],
    }, 5)

if not JOB.is_file():
    emit({"status": "BLOCKED_TRANSPORT", "next_gate": "A19C_KERNEL_VALIDATOR_MISSING"}, 6)

head = run("git", "rev-parse", "HEAD", timeout=30).stdout.strip()
proc = run(str(PYTHON), str(JOB.relative_to(ROOT)), timeout=180)
try:
    parsed = json.loads(proc.stdout)
except Exception:
    parsed = {}

if not isinstance(parsed, dict) or not parsed:
    emit({
        "status": "BLOCKED_TRANSPORT",
        "weather_head": head,
        "validator_returncode": proc.returncode,
        "next_gate": "A19C_RESULT_PARSE_FAILED",
        "stdout": proc.stdout[-12000:],
        "stderr": proc.stderr[-5000:],
    }, 7)

local_build_status = parsed.get("local_build_status")
research_gate_status = parsed.get("status")

# A correctly functioning fail-closed clock gate is research evidence, not an
# executor crash. The latest validator returns zero for both PASS_CLOCK_EVIDENCE
# and BLOCKED_REAL_CLOCK_EVIDENCE, while local validation failures remain nonzero.
transport_ok = bool(proc.returncode == 0 and local_build_status == "PASS")

emit({
    "status": "PASS" if transport_ok else "FAILED",
    "weather_head": head,
    "validator_returncode": proc.returncode,
    "local_build_status": local_build_status,
    "research_gate_status": research_gate_status,
    "checks": parsed.get("checks"),
    "clock_evidence": parsed.get("clock_evidence"),
    "next_gate": parsed.get("next_gate") or "A19C_RESULT_MISSING_NEXT_GATE",
    "stderr": proc.stderr[-5000:],
}, 0 if transport_ok else 8)
