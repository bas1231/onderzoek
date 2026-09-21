#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

ROOT = Path.home() / "prediction_research_weather"
PYTHON = Path.home() / "prediction_research/.venv/bin/python"
VALIDATOR = ROOT / "control/jobs/validate_madis_ldm_a19b.py"
REPORT = ROOT / "evidence/weather/WEATHER-AWAY-A19B-latest.json"
RAW = Path.home() / ".local/state/prediction-research/raw/madis_omo_public"


def run(*args: str, timeout: int = 300) -> dict:
    try:
        cp = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)
        return {
            "command": list(args),
            "returncode": cp.returncode,
            "stdout": cp.stdout[-30000:],
            "stderr": cp.stderr[-10000:],
        }
    except Exception as exc:
        return {
            "command": list(args),
            "returncode": None,
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}",
        }


def parse_obj(text: str) -> dict:
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


out = {
    "task": "WEATHER-A19B-V1-DIAG-REPLAY-SOURCE-V2",
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "diagnostic_complete": False,
}

if not ROOT.is_dir():
    out["diagnostic_error"] = "WEATHER_WORKTREE_MISSING"
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(2)
if not PYTHON.is_file():
    out["diagnostic_error"] = "PREDICTION_VENV_PYTHON_MISSING"
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(3)

out["git"] = {
    "branch": run("git", "branch", "--show-current", timeout=30).get("stdout", "").strip(),
    "head": run("git", "rev-parse", "HEAD", timeout=30).get("stdout", "").strip(),
    "status_tracked": run("git", "status", "--porcelain", "--untracked-files=no", timeout=30),
}

raw_files = []
if RAW.is_dir():
    for path in sorted(RAW.glob("*.gz"), key=lambda p: p.stat().st_mtime_ns):
        st = path.stat()
        raw_files.append({
            "path": str(path),
            "size": st.st_size,
            "mtime_ns": st.st_mtime_ns,
        })
out["a19a_replay_sources"] = {
    "directory": str(RAW),
    "count": len(raw_files),
    "latest": raw_files[-1] if raw_files else None,
}

if REPORT.is_file():
    try:
        out["existing_report"] = json.loads(REPORT.read_text(encoding="utf-8"))
    except Exception as exc:
        out["existing_report_error"] = f"{type(exc).__name__}: {exc}"
else:
    out["existing_report"] = None

if not VALIDATOR.is_file():
    out["diagnostic_error"] = "A19B_V1_VALIDATOR_MISSING"
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(4)

validation = run(str(PYTHON), str(VALIDATOR.relative_to(ROOT)), timeout=300)
out["validator_run"] = validation
parsed = parse_obj(validation.get("stdout", ""))
out["validator_parsed"] = parsed
checks = parsed.get("checks") if isinstance(parsed, dict) else None
out["failed_checks"] = []
if isinstance(checks, dict):
    for name, detail in checks.items():
        if isinstance(detail, dict) and detail.get("pass") is not True:
            out["failed_checks"].append(name)

out["diagnostic_complete"] = True
out["diagnosis"] = (
    "A19B_V1_PASS_NOW" if validation.get("returncode") == 0 and parsed.get("status") == "PASS"
    else "A19B_V1_REPRODUCED_FAILURE"
)
print(json.dumps(out, indent=2, sort_keys=True))
# Diagnostic success means evidence was collected; content may still show A19B failure.
raise SystemExit(0)
