#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import subprocess

ROOT = Path.home() / "prediction_research_weather"
PY = Path.home() / "prediction_research/.venv/bin/python"
VALIDATOR = ROOT / "control/jobs/validate_madis_ldm_a19b.py"
REPORT = ROOT / "evidence/weather/WEATHER-AWAY-A19B-latest.json"
RAW = Path.home() / ".local/state/prediction-research/raw/madis_omo_public"

out = {
    "task": "WEATHER-A19B-V1-DIAG-REPLAY-SOURCE",
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
}

files = []
if RAW.is_dir():
    for p in sorted(RAW.glob("*.gz"), key=lambda x: x.stat().st_mtime_ns):
        files.append({"path": str(p), "mtime_ns": p.stat().st_mtime_ns, "size": p.stat().st_size})
out["raw_files_tail"] = files[-5:]
out["latest_raw"] = files[-1] if files else None

if REPORT.is_file():
    try:
        out["current_report"] = json.loads(REPORT.read_text(encoding="utf-8"))
    except Exception as exc:
        out["current_report_error"] = f"{type(exc).__name__}: {exc}"

if VALIDATOR.is_file() and PY.is_file():
    cp = subprocess.run([str(PY), str(VALIDATOR.relative_to(ROOT))], cwd=ROOT, text=True, capture_output=True, timeout=300)
    out["validator_returncode"] = cp.returncode
    out["validator_stdout"] = cp.stdout[-30000:]
    out["validator_stderr"] = cp.stderr[-10000:]
else:
    out["validator_returncode"] = 2
    out["validator_stderr"] = "validator or python missing"

print(json.dumps(out, indent=2, sort_keys=True))
raise SystemExit(0)
