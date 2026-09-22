#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path.cwd()
TASK_ID = "WEATHER-CLOCK-A19C-DIAG-033"
WEATHER = Path.home() / "prediction_research_weather"


def run(*args: str, cwd: Path | None = None, timeout: int = 20) -> dict:
    try:
        cp = subprocess.run(args, cwd=cwd or ROOT, text=True, capture_output=True, timeout=timeout)
        return {
            "returncode": cp.returncode,
            "stdout": cp.stdout[-12000:],
            "stderr": cp.stderr[-6000:],
        }
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_read_error": f"{type(exc).__name__}: {exc}", "_path": str(path)}


out: dict[str, object] = {
    "task": "WX-A19C-DIAG-034",
    "source_task_id": TASK_ID,
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "economic_conclusion": "NO_PROVEN_EDGE",
}

result_path = ROOT / "control" / "results" / TASK_ID / "RESULT.json"
out["result_path_exists"] = result_path.is_file()
out["source_result"] = read_json(result_path) if result_path.is_file() else None

matches = []
for base in [ROOT / "control" / "tasks", ROOT / "control" / "lifecycle"]:
    if base.exists():
        for p in base.rglob(f"*{TASK_ID}*"):
            if p.is_file():
                matches.append({
                    "path": str(p),
                    "content": read_json(p) if p.suffix == ".json" else p.read_text(encoding="utf-8", errors="replace")[-12000:],
                })
out["task_and_lifecycle_matches"] = matches

if WEATHER.is_dir():
    out["weather_git"] = {
        "branch": run("git", "branch", "--show-current", cwd=WEATHER),
        "head": run("git", "rev-parse", "HEAD", cwd=WEATHER),
        "status": run("git", "status", "--porcelain", cwd=WEATHER),
        "recent": run("git", "log", "-8", "--oneline", cwd=WEATHER),
    }
    evidence = []
    evroot = WEATHER / "evidence" / "weather"
    if evroot.exists():
        for p in sorted(evroot.glob("*A19*.json"), key=lambda x: x.stat().st_mtime_ns, reverse=True)[:12]:
            evidence.append({
                "path": str(p),
                "content": read_json(p),
            })
    out["weather_evidence"] = evidence
else:
    out["weather_git"] = {"error": "WEATHER_WORKTREE_MISSING"}

clock: dict[str, object] = {}
if shutil.which("chronyc"):
    clock["chronyc_tracking"] = run("chronyc", "tracking", "-n")
else:
    clock["chronyc_tracking"] = {"status": "NOT_INSTALLED"}
if shutil.which("timedatectl"):
    clock["ntp_synchronized"] = run("timedatectl", "show", "-p", "NTPSynchronized", "--value")
    clock["timesync_status"] = run("timedatectl", "timesync-status")
else:
    clock["timedatectl"] = {"status": "NOT_AVAILABLE"}
out["clock_inventory"] = clock

print(json.dumps(out, indent=2, sort_keys=True))
