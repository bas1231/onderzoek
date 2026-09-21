#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

ROOT = Path.home() / "prediction_research_weather"
REPORT = ROOT / "evidence/weather/WEATHER-AWAY-A19B-latest.json"
V1_VALIDATOR = ROOT / "control/jobs/validate_madis_ldm_a19b.py"
V2_VALIDATOR = ROOT / "control/jobs/validate_madis_ldm_a19b_v2.py"
V2_PY = ROOT / "control/weather/madis_ldm_queue_ingest_a19b_v2.py"
V2_C = ROOT / "control/weather/madis_ldm_queue_reader_a19b_v2.c"


def run(*args: str, timeout: int = 60):
    try:
        cp = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)
        return {"returncode": cp.returncode, "stdout": cp.stdout[-12000:], "stderr": cp.stderr[-6000:]}
    except Exception as exc:
        return {"returncode": 999, "stdout": "", "stderr": f"{type(exc).__name__}: {exc}"}

out = {
    "task": "WEATHER-A19B-SOURCE-DIAG",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "economic_conclusion": "NO_PROVEN_EDGE",
    "weather_root_exists": ROOT.is_dir(),
}

if not ROOT.is_dir():
    out["status"] = "BLOCKED"
    out["reason"] = "WEATHER_WORKTREE_MISSING"
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(2)

out["branch"] = run("git", "branch", "--show-current")
out["head"] = run("git", "rev-parse", "HEAD")
out["status_porcelain_tracked"] = run("git", "status", "--porcelain", "--untracked-files=no")
out["remote_head"] = run("git", "rev-parse", "origin/ai/weather-madis-ldm-a19b")
out["files"] = {
    "v1_validator": V1_VALIDATOR.is_file(),
    "v2_validator": V2_VALIDATOR.is_file(),
    "v2_python": V2_PY.is_file(),
    "v2_c": V2_C.is_file(),
    "v1_report": REPORT.is_file(),
}

if REPORT.is_file():
    try:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
    except Exception as exc:
        report = {"parse_error": f"{type(exc).__name__}: {exc}"}
    out["v1_report_summary"] = {
        "status": report.get("status"),
        "next_gate": report.get("next_gate"),
        "generated_at": report.get("generated_at"),
        "validation_status": ((((report.get("steps") or {}).get("a19b_three_gate_validation") or {}).get("parsed") or {}).get("status")),
        "checks": ((((report.get("steps") or {}).get("a19b_three_gate_validation") or {}).get("parsed") or {}).get("checks")),
    }

out["status"] = "PASS"
print(json.dumps(out, indent=2, sort_keys=True))
