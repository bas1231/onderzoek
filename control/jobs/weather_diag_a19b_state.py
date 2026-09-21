#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

ROOT = Path.home() / "prediction_research_weather"
V1_REPORT = ROOT / "evidence/weather/WEATHER-AWAY-A19B-latest.json"
V1_VALIDATOR = ROOT / "control/jobs/validate_madis_ldm_a19b.py"
V2_VALIDATOR = ROOT / "control/jobs/validate_madis_ldm_a19b_v2.py"


def run(*args: str, timeout: int = 30) -> dict:
    cp = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)
    return {
        "returncode": cp.returncode,
        "stdout": cp.stdout[-8000:],
        "stderr": cp.stderr[-4000:],
    }


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception as exc:
        return {"_load_error": f"{type(exc).__name__}: {exc}"}


out: dict = {
    "task": "WEATHER-A19B-STATE-DIAG",
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
}

if not ROOT.is_dir():
    out["status"] = "BLOCKED"
    out["reason"] = "WEATHER_WORKTREE_MISSING"
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(2)

out["branch"] = run("git", "branch", "--show-current")
out["head"] = run("git", "rev-parse", "HEAD")
out["tracked_status"] = run("git", "status", "--porcelain", "--untracked-files=no")
out["v1_validator_exists"] = V1_VALIDATOR.is_file()
out["v2_validator_exists"] = V2_VALIDATOR.is_file()
out["v1_report_exists"] = V1_REPORT.is_file()

if V1_REPORT.is_file():
    report = load_json(V1_REPORT)
    parsed = ((((report.get("steps") or {}).get("a19b_three_gate_validation") or {}).get("parsed")) or {})
    out["v1_report"] = {
        "status": report.get("status"),
        "next_gate": report.get("next_gate"),
        "generated_at": report.get("generated_at"),
        "validation_status": parsed.get("status"),
        "a19b_v1_state": parsed.get("a19b_v1_state"),
        "queue_insertion_evidence_state": parsed.get("queue_insertion_evidence_state"),
        "checks": parsed.get("checks"),
    }

out["status"] = "PASS_DIAGNOSTIC"
print(json.dumps(out, indent=2, sort_keys=True))
