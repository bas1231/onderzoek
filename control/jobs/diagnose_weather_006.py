#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

MAIN = Path.home() / "prediction_research"
WX = Path.home() / "prediction_research_weather"
TASK_ID = "WEATHER-AWAY-A19B-BRIDGE-006"


def run(*args: str, cwd: Path):
    cp = subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=30)
    return {"returncode": cp.returncode, "stdout": cp.stdout[-8000:], "stderr": cp.stderr[-4000:]}


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_read_error": f"{type(exc).__name__}: {exc}", "_path": str(path)}

out = {
    "task": "DIAGNOSE-WEATHER-006",
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
}

result_path = MAIN / "control" / "results" / TASK_ID / "RESULT.json"
out["executor_result"] = read_json(result_path) if result_path.exists() else {"status": "MISSING", "path": str(result_path)}

candidates = list((MAIN / "control" / "tasks").glob(f"**/*{TASK_ID}*.json")) if (MAIN / "control" / "tasks").exists() else []
out["task_files"] = [{"path": str(p), "content": read_json(p)} for p in candidates]

lifecycle = MAIN / "control" / "lifecycle" / f"{TASK_ID}.json"
out["lifecycle"] = read_json(lifecycle) if lifecycle.exists() else {"status": "MISSING", "path": str(lifecycle)}

if WX.is_dir():
    out["weather_git"] = {
        "branch": run("git", "branch", "--show-current", cwd=WX),
        "head": run("git", "rev-parse", "HEAD", cwd=WX),
        "status": run("git", "status", "--porcelain", cwd=WX),
        "remote_head": run("git", "rev-parse", "origin/ai/weather-madis-ldm-a19b", cwd=WX),
    }
else:
    out["weather_git"] = {"status": "WORKTREE_MISSING"}

v1 = WX / "evidence" / "weather" / "WEATHER-AWAY-A19B-latest.json"
out["v1_report"] = read_json(v1) if v1.exists() else {"status": "MISSING"}

for rel in [
    "control/jobs/validate_madis_ldm_a19b_v2.py",
    "control/weather/madis_ldm_queue_native_a19b_v2.py",
    "control/weather/madis_ldm_queue_reader_a19b_v2.c",
    "control/weather/test_madis_ldm_a19b_v2.py",
    "control/weather/test_madis_ldm_a19b_v2_adversarial.py",
]:
    p = WX / rel
    out.setdefault("v2_files", {})[rel] = p.exists()

print(json.dumps(out, indent=2, sort_keys=True))
