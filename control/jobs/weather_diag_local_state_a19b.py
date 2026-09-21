#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

HOME = Path.home()
MAIN = HOME / "prediction_research"
WX = HOME / "prediction_research_weather"
OUT: dict[str, object] = {
    "task": "WEATHER-A19B-LOCAL-STATE-DIAG",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "economic_conclusion": "NO_PROVEN_EDGE",
}


def run(*args: str, cwd: Path) -> dict:
    try:
        cp = subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=30)
        return {"returncode": cp.returncode, "stdout": cp.stdout[-12000:], "stderr": cp.stderr[-6000:]}
    except Exception as exc:
        return {"returncode": 999, "error": f"{type(exc).__name__}: {exc}"}


def read_json(path: Path) -> object:
    if not path.is_file():
        return {"exists": False, "path": str(path)}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return {"exists": True, "path": str(path), "json": value}
    except Exception as exc:
        return {"exists": True, "path": str(path), "parse_error": f"{type(exc).__name__}: {exc}", "text_tail": path.read_text(encoding="utf-8", errors="replace")[-12000:]}

OUT["main_repo"] = {
    "head": run("git", "rev-parse", "HEAD", cwd=MAIN),
    "branch": run("git", "branch", "--show-current", cwd=MAIN),
    "status": run("git", "status", "--porcelain", cwd=MAIN),
}
OUT["weather_repo"] = {
    "head": run("git", "rev-parse", "HEAD", cwd=WX),
    "branch": run("git", "branch", "--show-current", cwd=WX),
    "status": run("git", "status", "--porcelain", cwd=WX),
    "remote_head": run("git", "rev-parse", "origin/ai/weather-madis-ldm-a19b", cwd=WX),
}
OUT["diag_012_result"] = read_json(MAIN / "control/results/WEATHER-A19B-DIAG-012/RESULT.json")
OUT["bridge_006_result"] = read_json(MAIN / "control/results/WEATHER-AWAY-A19B-BRIDGE-006/RESULT.json")
OUT["weather_v1_report"] = read_json(WX / "evidence/weather/WEATHER-AWAY-A19B-latest.json")
OUT["v2_files"] = {
    "validator": (WX / "control/jobs/validate_madis_ldm_a19b_v2.py").is_file(),
    "adapter": (WX / "control/weather/madis_ldm_queue_a19b_v2.py").is_file(),
    "reader_c": (WX / "control/weather/madis_ldm_queue_reader_a19b_v2.c").is_file(),
    "unit": (WX / "control/weather/test_madis_ldm_a19b_v2.py").is_file(),
    "adversarial": (WX / "control/weather/test_madis_ldm_a19b_v2_adversarial.py").is_file(),
}
print(json.dumps(OUT, indent=2, sort_keys=True))
