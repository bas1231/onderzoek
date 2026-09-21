#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

ROOT = Path.home() / "prediction_research_weather"
PYTHON = Path.home() / "prediction_research/.venv/bin/python"
BRANCH = "ai/weather-madis-ldm-a19b"
V1_JOB = ROOT / "control/jobs/weather_away_a19b.py"
V1_REPORT = ROOT / "evidence/weather/WEATHER-AWAY-A19B-latest.json"
V2_JOB = ROOT / "control/jobs/validate_madis_ldm_a19b_v2.py"


def run(*args: str, timeout: int = 1800):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)


def parse_obj(text: str) -> dict:
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


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

# Bring only the isolated Weather branch forward, and only by fast-forward.
pull = run("git", "pull", "--ff-only", "origin", BRANCH, timeout=120)
if pull.returncode != 0:
    emit({
        "status": "BLOCKED",
        "next_gate": "WEATHER_BRANCH_FAST_FORWARD_FAILED",
        "stdout": pull.stdout[-4000:],
        "stderr": pull.stderr[-4000:],
    }, 6)

head = run("git", "rev-parse", "HEAD", timeout=30).stdout.strip()
steps: dict[str, object] = {}

# Gate 1: A19B-v1. Reuse prior proof if present and valid; do not rerun blindly.
v1_obj = {}
if V1_REPORT.is_file():
    try:
        v1_obj = json.loads(V1_REPORT.read_text(encoding="utf-8"))
    except Exception:
        v1_obj = {}

v1_existing_pass = bool(
    v1_obj.get("status") == "PASS"
    and (((v1_obj.get("steps") or {}).get("a19b_three_gate_validation") or {}).get("parsed") or {}).get("status") == "PASS"
)

if v1_existing_pass:
    steps["a19b_v1"] = {
        "status": "ALREADY_SATISFIED",
        "report": str(V1_REPORT),
        "next_action": "ADVANCE_TO_A19B_V2",
    }
else:
    if not V1_JOB.is_file():
        emit({
            "status": "BLOCKED",
            "weather_head": head,
            "steps": steps,
            "next_gate": "A19B_V1_JOB_MISSING",
        }, 7)
    v1 = run(str(PYTHON), str(V1_JOB.relative_to(ROOT)), timeout=1200)
    steps["a19b_v1"] = {
        "status": "PASS" if v1.returncode == 0 else "FAILED",
        "returncode": v1.returncode,
        "stdout": v1.stdout[-10000:],
        "stderr": v1.stderr[-5000:],
    }
    if v1.returncode != 0:
        emit({
            "status": "BLOCKED_LOCAL_VALIDATION",
            "weather_head": head,
            "steps": steps,
            "next_gate": "FIX_A19B_V1_THREE_GATE_VALIDATION",
        }, 8)

# Gate 2: A19B-v2 queue-native local build/readiness.
if not V2_JOB.is_file():
    emit({
        "status": "BLOCKED_LOCAL_BUILD",
        "weather_head": head,
        "steps": steps,
        "next_gate": "A19B_V2_VALIDATOR_MISSING",
    }, 9)

v2 = run(str(PYTHON), str(V2_JOB.relative_to(ROOT)), timeout=1200)
v2_obj = parse_obj(v2.stdout)
steps["a19b_v2"] = {
    "status": v2_obj.get("status") or ("PASS" if v2.returncode == 0 else "FAILED"),
    "returncode": v2.returncode,
    "next_gate": v2_obj.get("next_gate"),
    "checks": v2_obj.get("checks"),
    "clock_readiness": v2_obj.get("clock_readiness"),
    "ldm_runtime_inventory": v2_obj.get("ldm_runtime_inventory"),
    "queue_insertion_evidence_state": v2_obj.get("queue_insertion_evidence_state"),
    "stderr": v2.stderr[-5000:],
}

if v2.returncode != 0 or v2_obj.get("status") != "PASS_LOCAL_BUILD":
    emit({
        "status": "BLOCKED_LOCAL_VALIDATION",
        "weather_head": head,
        "steps": steps,
        "next_gate": v2_obj.get("next_gate") or "FIX_A19B_V2_FAILED_CHECK",
        "terminal_for_current_authorization": False,
    }, 10)

next_gate = str(v2_obj.get("next_gate") or "UNKNOWN_A19B_V2_GATE")
external_or_system_gate = next_gate in {
    "BLOCKED_CLOCK_EVIDENCE",
    "BLOCKED_NOAA_MADIS_LDM_ACCESS_OR_RUNTIME",
}

emit({
    "status": "COMPLETED_LOCAL_RESEARCH_GATE",
    "weather_head": head,
    "steps": steps,
    "next_gate": next_gate,
    "a19b_v1_rerun_policy": "DO_NOT_REPEAT_WHILE_VALID_PASS_REPORT_EXISTS",
    "a19b_v2_local_build": "PASS",
    "terminal_for_current_authorization": external_or_system_gate,
}, 0)
