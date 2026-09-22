#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

ROOT = Path.home() / "prediction_research_weather"
REPORT = ROOT / "evidence/weather/WEATHER-AWAY-A19B-latest.json"


def run(*args: str):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=30)

out = {
    "task": "WEATHER-INSPECT-A19B-LOCAL",
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
}

if not ROOT.is_dir():
    out.update(status="BLOCKED", reason="WEATHER_WORKTREE_MISSING")
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(2)

out["branch"] = run("git", "branch", "--show-current").stdout.strip()
out["head"] = run("git", "rev-parse", "HEAD").stdout.strip()
out["tracked_status"] = run("git", "status", "--porcelain", "--untracked-files=no").stdout.strip()

if not REPORT.is_file():
    out.update(status="BLOCKED", reason="A19B_REPORT_MISSING", report=str(REPORT))
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(3)

try:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
except Exception as exc:
    out.update(status="BLOCKED", reason="A19B_REPORT_PARSE_FAILED", detail=f"{type(exc).__name__}: {exc}")
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(4)

validation = (((report.get("steps") or {}).get("a19b_three_gate_validation") or {}).get("parsed") or {})
runner = (((report.get("steps") or {}).get("a19b_three_gate_validation") or {}).get("runner") or {})
out.update({
    "status": "PASS" if validation.get("status") == "PASS" else "BLOCKED",
    "report_status": report.get("status"),
    "report_generated_at": report.get("generated_at"),
    "next_gate": report.get("next_gate"),
    "validation_status": validation.get("status"),
    "a19b_v1_state": validation.get("a19b_v1_state"),
    "queue_insertion_evidence_state": validation.get("queue_insertion_evidence_state"),
    "checks": validation.get("checks"),
    "validation_runner_returncode": runner.get("returncode"),
    "validation_runner_stderr": runner.get("stderr"),
    "clock_readiness": (report.get("steps") or {}).get("clock_readiness"),
    "report": str(REPORT),
})
print(json.dumps(out, indent=2, sort_keys=True))
raise SystemExit(0)
