#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

ROOT = Path.home() / "prediction_research_weather"
REPORT = ROOT / "evidence/weather/WEATHER-AWAY-A19B-latest.json"
V1_VALIDATOR = ROOT / "control/jobs/validate_madis_ldm_a19b.py"
V2_VALIDATOR = ROOT / "control/jobs/validate_madis_ldm_a19b_v2.py"
V2_READER = ROOT / "control/weather/madis_ldm_queue_reader_a19b_v2.c"
V2_ADAPTER = ROOT / "control/weather/madis_ldm_queue_a19b_v2.py"


def sh(*args: str):
    try:
        cp = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=30)
        return {"returncode": cp.returncode, "stdout": cp.stdout.strip(), "stderr": cp.stderr.strip()}
    except Exception as exc:
        return {"returncode": 999, "error": f"{type(exc).__name__}: {exc}"}

out = {
    "task": "WEATHER-A19B-SOURCE-DIAG",
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "root_exists": ROOT.is_dir(),
}

if not ROOT.is_dir():
    out["status"] = "BLOCKED"
    out["reason"] = "WEATHER_WORKTREE_MISSING"
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(2)

out["branch"] = sh("git", "branch", "--show-current")
out["head"] = sh("git", "rev-parse", "HEAD")
out["status_porcelain_tracked"] = sh("git", "status", "--porcelain", "--untracked-files=no")
out["remote_branch_head"] = sh("git", "rev-parse", "origin/ai/weather-madis-ldm-a19b")
out["files"] = {
    "v1_validator": V1_VALIDATOR.is_file(),
    "v2_validator": V2_VALIDATOR.is_file(),
    "v2_reader": V2_READER.is_file(),
    "v2_adapter": V2_ADAPTER.is_file(),
}

if REPORT.is_file():
    try:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        parsed = (((report.get("steps") or {}).get("a19b_three_gate_validation") or {}).get("parsed") or {})
        out["v1_report"] = {
            "status": report.get("status"),
            "generated_at": report.get("generated_at"),
            "next_gate": report.get("next_gate"),
            "validation_status": parsed.get("status"),
            "validation_checks": parsed.get("checks"),
            "a19b_v1_state": parsed.get("a19b_v1_state"),
            "queue_insertion_evidence_state": parsed.get("queue_insertion_evidence_state"),
        }
    except Exception as exc:
        out["v1_report_error"] = f"{type(exc).__name__}: {exc}"
else:
    out["v1_report"] = None

out["status"] = "PASS_DIAGNOSTIC"
print(json.dumps(out, indent=2, sort_keys=True))
