#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

ROOT = Path.home() / "prediction_research_weather"
REPORT = ROOT / "evidence/weather/WEATHER-AWAY-A19B-latest.json"
BRANCH = "ai/weather-madis-ldm-a19b"


def run(*args: str, timeout: int = 30) -> dict:
    try:
        cp = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)
        return {
            "command": list(args),
            "returncode": cp.returncode,
            "stdout": cp.stdout[-8000:],
            "stderr": cp.stderr[-4000:],
        }
    except Exception as exc:
        return {
            "command": list(args),
            "returncode": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


out = {
    "task": "WEATHER-A19B-V1-DIAG-READONLY",
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "weather_root_exists": ROOT.is_dir(),
    "report_exists": REPORT.is_file(),
}

if not ROOT.is_dir():
    out["status"] = "BLOCKED"
    out["next_gate"] = "WEATHER_WORKTREE_MISSING"
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(2)

out["git"] = {
    "branch": run("git", "branch", "--show-current"),
    "head": run("git", "rev-parse", "HEAD"),
    "status_tracked": run("git", "status", "--porcelain", "--untracked-files=no"),
    "origin_weather_head": run("git", "rev-parse", f"origin/{BRANCH}"),
}

if REPORT.is_file():
    try:
        obj = json.loads(REPORT.read_text(encoding="utf-8"))
        out["report"] = obj
        parsed = (((obj.get("steps") or {}).get("a19b_three_gate_validation") or {}).get("parsed") or {})
        checks = parsed.get("checks") or {}
        failed = [name for name, value in checks.items() if isinstance(value, dict) and value.get("pass") is False]
        out["diagnosis"] = {
            "report_status": obj.get("status"),
            "validator_status": parsed.get("status"),
            "a19b_v1_state": parsed.get("a19b_v1_state"),
            "failed_checks": failed,
            "validator_next_gate": parsed.get("next_gate"),
        }
        out["status"] = "PASS"
        out["next_gate"] = "REPAIR_FAILED_CHECK" if failed else "A19B_V1_EVIDENCE_CONSISTENT"
    except Exception as exc:
        out["status"] = "BLOCKED"
        out["next_gate"] = "MALFORMED_A19B_REPORT"
        out["report_error"] = f"{type(exc).__name__}: {exc}"
else:
    out["status"] = "BLOCKED"
    out["next_gate"] = "A19B_REPORT_MISSING"

print(json.dumps(out, indent=2, sort_keys=True))
raise SystemExit(0 if out["status"] == "PASS" else 1)
