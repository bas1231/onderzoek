#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path.home() / "prediction_research_weather"
V1_REPORT = ROOT / "evidence/weather/WEATHER-AWAY-A19B-latest.json"
V2_FILES = [
    ROOT / "control/jobs/validate_madis_ldm_a19b_v2.py",
    ROOT / "control/weather/madis_ldm_queue_native_a19b_v2.py",
    ROOT / "control/weather/madis_ldm_queue_reader_a19b_v2.c",
    ROOT / "control/weather/test_madis_ldm_queue_native_a19b_v2.py",
    ROOT / "control/weather/test_madis_ldm_queue_native_a19b_v2_adversarial.py",
]


def run(*args: str, timeout: int = 30) -> dict:
    try:
        cp = subprocess.run(args, cwd=ROOT if ROOT.is_dir() else None, text=True,
                            capture_output=True, timeout=timeout)
        return {
            "returncode": cp.returncode,
            "stdout": cp.stdout[-12000:],
            "stderr": cp.stderr[-6000:],
        }
    except Exception as exc:
        return {"returncode": None, "error": f"{type(exc).__name__}: {exc}"}


out = {
    "task": "WEATHER-A19B-STATE-DIAG-V2",
    "weather_root": str(ROOT),
    "weather_root_exists": ROOT.is_dir(),
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
}

if ROOT.is_dir():
    out["branch"] = run("git", "branch", "--show-current")
    out["head"] = run("git", "rev-parse", "HEAD")
    out["origin_head"] = run("git", "rev-parse", "origin/ai/weather-madis-ldm-a19b")
    out["status_tracked"] = run("git", "status", "--porcelain", "--untracked-files=no")
    out["status_all"] = run("git", "status", "--porcelain")
    out["recent_commits"] = run("git", "log", "-8", "--oneline", "--decorate")

out["v2_files"] = {
    str(p.relative_to(ROOT)) if ROOT.is_dir() else str(p): p.is_file()
    for p in V2_FILES
}

if V1_REPORT.is_file():
    try:
        report = json.loads(V1_REPORT.read_text(encoding="utf-8"))
        parsed = (((report.get("steps") or {}).get("a19b_three_gate_validation") or {}).get("parsed") or {})
        out["v1_report"] = {
            "status": report.get("status"),
            "generated_at": report.get("generated_at"),
            "next_gate": report.get("next_gate"),
            "validation_status": parsed.get("status"),
            "validation_checks": parsed.get("checks"),
        }
    except Exception as exc:
        out["v1_report"] = {"parse_error": f"{type(exc).__name__}: {exc}"}
else:
    out["v1_report"] = {"exists": False}

out["clock_inventory"] = {
    "chronyc": shutil.which("chronyc"),
    "timedatectl": shutil.which("timedatectl"),
}
if shutil.which("chronyc"):
    out["chronyc_tracking"] = run("chronyc", "tracking", "-n", timeout=5)
if shutil.which("timedatectl"):
    out["ntp_sync"] = run("timedatectl", "show", "-p", "NTPSynchronized", "--value", timeout=5)

out["ldm_inventory"] = {
    name: shutil.which(name) for name in ("ldmd", "pqcheck", "pqcat", "pqact")
}

print(json.dumps(out, indent=2, sort_keys=True))
raise SystemExit(0)
