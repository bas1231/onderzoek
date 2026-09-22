#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

MAIN = Path.home() / "prediction_research"
WEATHER = Path.home() / "prediction_research_weather"
TASK_ID = "WEATHER-CLOCK-GATE-028-INSPECT-029"
RESULT = MAIN / "control" / "results" / TASK_ID / "RESULT.json"
EVIDENCE = WEATHER / "evidence" / "weather"


def run(args: list[str], cwd: Path | None = None, timeout: int = 10) -> dict:
    try:
        cp = subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=timeout)
        return {
            "command": args,
            "returncode": cp.returncode,
            "stdout": cp.stdout[-12000:],
            "stderr": cp.stderr[-6000:],
        }
    except Exception as exc:
        return {"command": args, "error": f"{type(exc).__name__}: {exc}"}


def read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"read_error": f"{type(exc).__name__}: {exc}", "path": str(path)}


out: dict[str, object] = {
    "task": "WEATHER-CLOCK-GATE-029-DIAG",
    "target_task_id": TASK_ID,
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "economic_conclusion": "NO_PROVEN_EDGE",
}

out["target_result"] = read_json(RESULT) if RESULT.is_file() else {
    "status": "NOT_FOUND",
    "path": str(RESULT),
}

for label, root in (("main", MAIN), ("weather", WEATHER)):
    if root.is_dir():
        out[f"{label}_git"] = {
            "head": run(["git", "rev-parse", "HEAD"], cwd=root),
            "branch": run(["git", "branch", "--show-current"], cwd=root),
            "tracked_status": run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=root),
        }
    else:
        out[f"{label}_git"] = {"status": "WORKTREE_MISSING", "path": str(root)}

clock: dict[str, object] = {
    "chronyc_path": shutil.which("chronyc"),
    "timedatectl_path": shutil.which("timedatectl"),
}
if shutil.which("chronyc"):
    clock["chronyc_tracking"] = run(["chronyc", "tracking", "-n"])
if shutil.which("timedatectl"):
    clock["ntp_synchronized"] = run(["timedatectl", "show", "-p", "NTPSynchronized", "--value"])
out["clock"] = clock

ldm_names = ["ldmd", "pqcheck", "pqcat", "pqact", "pqmon"]
out["ldm_runtime"] = {name: shutil.which(name) for name in ldm_names}

latest: list[dict[str, object]] = []
if EVIDENCE.is_dir():
    files = sorted(EVIDENCE.glob("*.json"), key=lambda p: p.stat().st_mtime_ns, reverse=True)[:12]
    for path in files:
        obj = read_json(path)
        latest.append({
            "path": str(path),
            "mtime_ns": path.stat().st_mtime_ns,
            "content": obj,
        })
out["latest_weather_evidence"] = latest

print(json.dumps(out, indent=2, sort_keys=True))
