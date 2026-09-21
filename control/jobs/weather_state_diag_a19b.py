#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

ROOT = Path.home() / "prediction_research_weather"
REPORT = ROOT / "evidence/weather/WEATHER-AWAY-A19B-latest.json"
V1_VALIDATOR = ROOT / "control/jobs/validate_madis_ldm_a19b.py"
V2_VALIDATOR = ROOT / "control/jobs/validate_madis_ldm_a19b_v2.py"
V2_ADAPTER = ROOT / "control/weather/madis_ldm_queue_a19b_v2.py"
V2_READER = ROOT / "control/weather/madis_ldm_queue_reader_a19b_v2.c"


def run(*args: str) -> dict:
    try:
        cp = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=30)
        return {"returncode": cp.returncode, "stdout": cp.stdout[-8000:], "stderr": cp.stderr[-4000:]}
    except Exception as exc:
        return {"returncode": 99, "error": f"{type(exc).__name__}: {exc}"}

out: dict = {
    "task": "WEATHER-A19B-STATE-DIAG",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "economic_conclusion": "NO_PROVEN_EDGE",
    "weather_root_exists": ROOT.is_dir(),
}

if ROOT.is_dir():
    out["branch"] = run("git", "branch", "--show-current")
    out["head"] = run("git", "rev-parse", "HEAD")
    out["status_tracked"] = run("git", "status", "--porcelain", "--untracked-files=no")
    out["origin_weather_head"] = run("git", "rev-parse", "origin/ai/weather-madis-ldm-a19b")
    out["files"] = {
        "v1_validator": V1_VALIDATOR.is_file(),
        "v2_validator": V2_VALIDATOR.is_file(),
        "v2_adapter": V2_ADAPTER.is_file(),
        "v2_reader": V2_READER.is_file(),
        "report": REPORT.is_file(),
    }

    if REPORT.is_file():
        try:
            report = json.loads(REPORT.read_text(encoding="utf-8"))
            v1 = (((report.get("steps") or {}).get("a19b_three_gate_validation") or {}).get("parsed") or {})
            out["report_summary"] = {
                "status": report.get("status"),
                "generated_at": report.get("generated_at"),
                "next_gate": report.get("next_gate"),
                "v1_status": v1.get("status"),
                "v1_state": v1.get("a19b_v1_state"),
                "v1_next_gate": v1.get("next_gate"),
                "checks": v1.get("checks"),
            }
        except Exception as exc:
            out["report_parse_error"] = f"{type(exc).__name__}: {exc}"

print(json.dumps(out, indent=2, sort_keys=True))
