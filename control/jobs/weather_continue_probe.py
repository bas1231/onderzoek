#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

MAIN = Path.home() / "prediction_research"
WEATHER = Path.home() / "prediction_research_weather"
RESULT = MAIN / "control/results/WEATHER-CLOCK-A19C-GATE-039/RESULT.json"
EVIDENCE = WEATHER / "evidence/weather"


def run(*args: str, cwd: Path) -> dict:
    try:
        cp = subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=30)
        return {"returncode": cp.returncode, "stdout": cp.stdout.strip(), "stderr": cp.stderr.strip()}
    except Exception as exc:
        return {"returncode": 999, "error": f"{type(exc).__name__}: {exc}"}

out = {
    "task": "WEATHER-CONTINUE-PROBE",
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "result_039": None,
    "weather": {},
    "evidence": [],
}

if RESULT.is_file():
    try:
        out["result_039"] = json.loads(RESULT.read_text(encoding="utf-8"))
    except Exception as exc:
        out["result_039"] = {"parse_error": f"{type(exc).__name__}: {exc}"}
else:
    out["result_039"] = {"status": "MISSING_LOCAL_RESULT"}

if WEATHER.is_dir():
    out["weather"]["branch"] = run("git", "branch", "--show-current", cwd=WEATHER)
    out["weather"]["head"] = run("git", "rev-parse", "HEAD", cwd=WEATHER)
    out["weather"]["status"] = run("git", "status", "--porcelain", cwd=WEATHER)
    out["weather"]["log"] = run("git", "log", "-8", "--oneline", cwd=WEATHER)

if EVIDENCE.is_dir():
    files = sorted(
        [p for p in EVIDENCE.iterdir() if p.is_file()],
        key=lambda p: p.stat().st_mtime_ns,
        reverse=True,
    )[:12]
    for p in files:
        item = {"name": p.name, "size": p.stat().st_size}
        if p.suffix == ".json":
            try:
                obj = json.loads(p.read_text(encoding="utf-8"))
                item["status"] = obj.get("status")
                item["next_gate"] = obj.get("next_gate")
                item["task"] = obj.get("task")
                item["generated_at"] = obj.get("generated_at")
            except Exception as exc:
                item["parse_error"] = type(exc).__name__
        out["evidence"].append(item)

print(json.dumps(out, indent=2, sort_keys=True))
