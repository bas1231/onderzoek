#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

ROOT = Path.home() / "prediction_research_weather"
PYTHON = Path.home() / "prediction_research/.venv/bin/python"
REPORT = ROOT / "evidence/weather/WEATHER-AWAY-A19B-latest.json"
VALIDATOR = ROOT / "control/jobs/validate_madis_ldm_a19b.py"
RAW = Path.home() / ".local/state/prediction-research/raw/madis_omo_public"


def run(*args: str, timeout: int = 300) -> dict:
    try:
        cp = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)
        return {
            "command": list(args),
            "returncode": cp.returncode,
            "stdout": cp.stdout[-30000:],
            "stderr": cp.stderr[-15000:],
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": list(args),
            "returncode": 124,
            "stdout": (exc.stdout or "")[-30000:] if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "")[-15000:] if isinstance(exc.stderr, str) else "",
            "timed_out": True,
        }


def read_json(path: Path):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except Exception as exc:
        return {"_read_error": f"{type(exc).__name__}: {exc}"}


out = {
    "task": "WEATHER-A19B-V1-DIAG-024",
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "openai_api": False,
}

if not ROOT.is_dir():
    out.update(status="BLOCKED", reason="WEATHER_WORKTREE_MISSING")
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(2)
if not PYTHON.is_file():
    out.update(status="BLOCKED", reason="PREDICTION_VENV_PYTHON_MISSING")
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(3)

out["git_branch"] = run("git", "branch", "--show-current", timeout=30)
out["git_head"] = run("git", "rev-parse", "HEAD", timeout=30)
out["git_status_tracked"] = run("git", "status", "--porcelain", "--untracked-files=no", timeout=30)
out["git_status_all"] = run("git", "status", "--porcelain", timeout=30)
out["existing_report"] = read_json(REPORT) if REPORT.is_file() else None
out["validator_exists"] = VALIDATOR.is_file()
out["raw_dir_exists"] = RAW.is_dir()
out["latest_raw"] = None
if RAW.is_dir():
    files = sorted(RAW.glob("*.gz"), key=lambda p: p.stat().st_mtime_ns)
    if files:
        p = files[-1]
        out["latest_raw"] = {
            "path": str(p),
            "size": p.stat().st_size,
            "mtime_ns": p.stat().st_mtime_ns,
        }

if not VALIDATOR.is_file():
    out.update(status="BLOCKED", reason="A19B_V1_VALIDATOR_MISSING")
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(4)

validation = run(str(PYTHON), str(VALIDATOR.relative_to(ROOT)), timeout=300)
out["validator_run"] = validation
try:
    parsed = json.loads(validation["stdout"])
    out["validator_parsed"] = parsed if isinstance(parsed, dict) else None
except Exception as exc:
    out["validator_parse_error"] = f"{type(exc).__name__}: {exc}"
    out["validator_parsed"] = None

out["status"] = "DIAG_COMPLETE"
out["validator_returncode"] = validation["returncode"]
print(json.dumps(out, indent=2, sort_keys=True))
raise SystemExit(0)
