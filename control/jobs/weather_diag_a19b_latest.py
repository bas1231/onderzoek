#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

root = Path.home() / "prediction_research_weather"
report = root / "evidence/weather/WEATHER-AWAY-A19B-latest.json"
raw_dir = Path.home() / ".local/state/prediction-research/raw/madis_omo_public"


def run(*args: str):
    cp = subprocess.run(args, cwd=root, text=True, capture_output=True, timeout=30)
    return {"returncode": cp.returncode, "stdout": cp.stdout[-8000:], "stderr": cp.stderr[-4000:]}

out = {
    "task": "WEATHER-A19B-DIAGNOSTIC",
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "git_head": run("git", "rev-parse", "HEAD"),
    "git_branch": run("git", "branch", "--show-current"),
    "git_status_tracked": run("git", "status", "--porcelain", "--untracked-files=no"),
    "report_exists": report.is_file(),
}

if report.is_file():
    try:
        out["report"] = json.loads(report.read_text(encoding="utf-8"))
    except Exception as exc:
        out["report_error"] = f"{type(exc).__name__}: {exc}"

if raw_dir.is_dir():
    files = sorted(raw_dir.glob("*.gz"), key=lambda p: p.stat().st_mtime_ns, reverse=True)[:5]
    out["latest_a19a_raw"] = [
        {"path": str(p), "size": p.stat().st_size, "mtime_ns": p.stat().st_mtime_ns}
        for p in files
    ]
else:
    out["latest_a19a_raw"] = []

print(json.dumps(out, indent=2, sort_keys=True))
