#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

ROOT = Path.home() / "prediction_research_weather"
PYTHON = Path.home() / "prediction_research/.venv/bin/python"
BRANCH = "ai/weather-madis-ldm-a19b"
KERNEL_VALIDATOR = ROOT / "control/jobs/validate_clock_evidence_kernel_a19c.py"
SNTP_VALIDATOR = ROOT / "control/jobs/validate_clock_evidence_a19c.py"


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

if not KERNEL_VALIDATOR.is_file():
    finish({
        "status": "BLOCKED_LOCAL_BUILD",
        "weather_head": head,
        "next_gate": "LATEST_A19C_KERNEL_VALIDATOR_MISSING",
    }, 7)

kernel = run(str(PYTHON), str(KERNEL_VALIDATOR.relative_to(ROOT)), timeout=120)
kobj = parse(kernel.stdout)
steps = {
    "latest_a19c_kernel_clock": {
        "returncode": kernel.returncode,
        "status": kobj.get("status"),
        "next_gate": kobj.get("next_gate"),
        "checks": kobj.get("checks"),
        "clock_evidence": kobj.get("clock_evidence"),
        "stderr": kernel.stderr[-4000:],
    }
}

if kernel.returncode != 0 or kobj.get("local_build_status") != "PASS":
    finish({
        "status": "BLOCKED_LOCAL_VALIDATION",
        "weather_head": head,
        "steps": steps,
        "next_gate": kobj.get("next_gate") or "FIX_A19C_LATEST_LOCAL_VALIDATION",
        "terminal_for_current_authorization": False,
    }, 8)

if kobj.get("status") != "PASS_CLOCK_EVIDENCE":
    finish({
        "status": "COMPLETED_LOCAL_RESEARCH_GATE",
        "weather_head": head,
        "steps": steps,
        "next_gate": kobj.get("next_gate") or "CLOCK_EVIDENCE_TRANSPORT_OR_SYSTEM_SYNC",
        "terminal_for_current_authorization": True,
    }, 0)

# Independent external UTC sanity check. This is read-only UDP SNTP and never
# changes the local clock. Failure to obtain evidence is a research gate, not a
# technical kernel-build failure.
if not SNTP_VALIDATOR.is_file():
    finish({
        "status": "COMPLETED_LOCAL_RESEARCH_GATE",
        "weather_head": head,
        "steps": steps,
        "next_gate": "A19C_EXTERNAL_UTC_VALIDATOR_MISSING",
        "terminal_for_current_authorization": False,
    }, 9)

sntp = run(str(PYTHON), str(SNTP_VALIDATOR.relative_to(ROOT)), timeout=120)
sobj = parse(sntp.stdout)
steps["a19c_external_sntp_crosscheck"] = {
    "returncode": sntp.returncode,
    "status": sobj.get("status"),
    "next_gate": sobj.get("next_gate"),
    "checks": sobj.get("checks"),
    "clock_readiness": sobj.get("clock_readiness"),
    "stderr": sntp.stderr[-4000:],
}

if sntp.returncode != 0 or sobj.get("local_build_status") != "PASS":
    finish({
        "status": "BLOCKED_LOCAL_VALIDATION",
        "weather_head": head,
        "steps": steps,
        "next_gate": sobj.get("next_gate") or "FIX_A19C_SNTP_LOCAL_VALIDATION",
        "terminal_for_current_authorization": False,
    }, 10)

if sobj.get("status") == "PASS_CLOCK_EVIDENCE":
    next_gate = "BLOCKED_NOAA_MADIS_LDM_ACCESS_OR_RUNTIME"
else:
    next_gate = sobj.get("next_gate") or "CLOCK_EXTERNAL_UTC_CROSSCHECK_BLOCKED"

finish({
    "status": "COMPLETED_A19C_CLOCK_GATE",
    "weather_head": head,
    "steps": steps,
    "next_gate": next_gate,
    "terminal_for_current_authorization": True,
}, 0)
