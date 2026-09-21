#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

ROOT = Path.home() / "prediction_research_weather"
PY = Path.home() / "prediction_research/.venv/bin/python"
BRANCH = "ai/weather-madis-ldm-a19b"
PROBE = ROOT / "control/jobs/probe_clock_evidence_a19b_v2.py"


def emit(obj: dict, code: int = 0) -> None:
    obj.update({
        "economic_conclusion": "NO_PROVEN_EDGE",
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
    })
    print(json.dumps(obj, indent=2, sort_keys=True))
    raise SystemExit(code)

if not ROOT.is_dir() or not PY.is_file():
    emit({"status": "BLOCKED", "next_gate": "LOCAL_WEATHER_RUNTIME_MISSING"}, 2)

branch = subprocess.run(["git", "branch", "--show-current"], cwd=ROOT, text=True, capture_output=True, timeout=30)
if branch.returncode != 0 or branch.stdout.strip() != BRANCH:
    emit({"status": "BLOCKED", "next_gate": "WRONG_WEATHER_BRANCH", "actual": branch.stdout.strip()}, 3)

tracked = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, text=True, capture_output=True, timeout=30)
if tracked.returncode != 0 or tracked.stdout.strip():
    emit({"status": "BLOCKED", "next_gate": "WEATHER_WORKTREE_TRACKED_CHANGES", "detail": tracked.stdout[-4000:]}, 4)

pull = subprocess.run(["git", "pull", "--ff-only", "origin", BRANCH], cwd=ROOT, text=True, capture_output=True, timeout=120)
if pull.returncode != 0:
    emit({"status": "BLOCKED", "next_gate": "WEATHER_BRANCH_FAST_FORWARD_FAILED", "stderr": pull.stderr[-4000:]}, 5)

if not PROBE.is_file():
    emit({"status": "BLOCKED", "next_gate": "CLOCK_PROBE_MISSING"}, 6)

cp = subprocess.run([str(PY), str(PROBE.relative_to(ROOT))], cwd=ROOT, text=True, capture_output=True, timeout=30)
try:
    parsed = json.loads(cp.stdout)
except Exception:
    parsed = {}

emit({
    "status": "COMPLETED_CLOCK_PROBE" if cp.returncode == 0 else "CLOCK_PROBE_FAILED",
    "probe_returncode": cp.returncode,
    "probe": parsed,
    "stdout": cp.stdout[-12000:],
    "stderr": cp.stderr[-4000:],
    "next_gate": parsed.get("next_gate") or "CLOCK_PROBE_PARSE_FAILURE",
}, 0 if cp.returncode == 0 else 7)
