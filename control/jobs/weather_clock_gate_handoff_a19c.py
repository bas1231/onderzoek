#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

ROOT = Path.home() / "prediction_research_weather"
PYTHON = Path.home() / "prediction_research/.venv/bin/python"
BRANCH = "ai/weather-madis-ldm-a19b"
A19C = ROOT / "control/jobs/validate_clock_evidence_a19c.py"
KERNEL_PROBE = ROOT / "control/jobs/probe_kernel_clock_a19b_v2.py"


def run(*args: str, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)


def parse_obj(text: str) -> dict:
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def finish(payload: dict, code: int = 0) -> None:
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

branch = run("git", "branch", "--show-current", timeout=30)
if branch.returncode != 0 or branch.stdout.strip() != BRANCH:
    finish({
        "status": "BLOCKED",
        "next_gate": "WRONG_WEATHER_BRANCH",
        "actual_branch": branch.stdout.strip(),
    }, 4)

tracked = run("git", "status", "--porcelain", "--untracked-files=no", timeout=30)
if tracked.returncode != 0 or tracked.stdout.strip():
    finish({
        "status": "BLOCKED",
        "next_gate": "WEATHER_WORKTREE_TRACKED_CHANGES",
        "detail": tracked.stdout[-4000:] or tracked.stderr[-4000:],
    }, 5)

pull = run("git", "pull", "--ff-only", "origin", BRANCH, timeout=120)
if pull.returncode != 0:
    finish({
        "status": "BLOCKED",
        "next_gate": "WEATHER_BRANCH_FAST_FORWARD_FAILED",
        "stdout": pull.stdout[-4000:],
        "stderr": pull.stderr[-4000:],
    }, 6)

head = run("git", "rev-parse", "HEAD", timeout=30).stdout.strip()

if not A19C.is_file():
    finish({
        "status": "BLOCKED_LOCAL_BUILD",
        "weather_head": head,
        "next_gate": "A19C_VALIDATOR_MISSING",
    }, 7)

clock_run = run(str(PYTHON), str(A19C.relative_to(ROOT)), timeout=180)
clock = parse_obj(clock_run.stdout)
steps: dict[str, object] = {
    "a19c_three_gate": {
        "returncode": clock_run.returncode,
        "status": clock.get("status"),
        "next_gate": clock.get("next_gate"),
        "checks": clock.get("checks"),
        "local_build_status": clock.get("local_build_status"),
        "clock_readiness": clock.get("clock_readiness"),
        "stderr": clock_run.stderr[-4000:],
    }
}

if clock_run.returncode != 0 or clock.get("local_build_status") != "PASS":
    finish({
        "status": "BLOCKED_LOCAL_VALIDATION",
        "weather_head": head,
        "steps": steps,
        "next_gate": clock.get("next_gate") or "FIX_A19C_LOCAL_VALIDATION",
        "terminal_for_current_authorization": False,
    }, 8)

if clock.get("status") == "PASS_CLOCK_EVIDENCE":
    finish({
        "status": "COMPLETED_CLOCK_GATE",
        "weather_head": head,
        "steps": steps,
        "clock_gate": "PASS",
        "next_gate": "BLOCKED_NOAA_MADIS_LDM_ACCESS_OR_RUNTIME",
        "terminal_for_current_authorization": True,
    }, 0)

# SNTP did not provide bounded live evidence. Collect the already-built,
# read-only Linux kernel NTP-discipline probe before declaring the gate blocked.
if not KERNEL_PROBE.is_file():
    finish({
        "status": "COMPLETED_CLOCK_GATE",
        "weather_head": head,
        "steps": steps,
        "clock_gate": "BLOCKED",
        "next_gate": "KERNEL_CLOCK_PROBE_MISSING",
        "terminal_for_current_authorization": True,
    }, 0)

kernel_run = run(str(PYTHON), str(KERNEL_PROBE.relative_to(ROOT)), timeout=60)
kernel = parse_obj(kernel_run.stdout)
steps["kernel_clock_probe"] = {
    "returncode": kernel_run.returncode,
    "status": kernel.get("status"),
    "decision": kernel.get("decision"),
    "observed": kernel.get("observed"),
    "valid_sample_count": kernel.get("valid_sample_count"),
    "timedatectl_ntp_synchronized": kernel.get("timedatectl_ntp_synchronized"),
    "stderr": kernel_run.stderr[-4000:],
}

finish({
    "status": "COMPLETED_CLOCK_GATE_DIAGNOSTIC",
    "weather_head": head,
    "steps": steps,
    "clock_gate": "BLOCKED_PENDING_EVIDENCE_REVIEW",
    "next_gate": "REVIEW_KERNEL_CLOCK_EVIDENCE_OR_IMPROVE_CLOCK_EVIDENCE_TRANSPORT",
    "terminal_for_current_authorization": True,
}, 0)
