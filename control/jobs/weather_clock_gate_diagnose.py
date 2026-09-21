#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path.cwd()
HOME = Path.home()
WEATHER_ROOT = HOME / "prediction_research_weather"
RESULT_028 = ROOT / "control/results/WEATHER-A19B-V2-CLOCK-GATE-028/RESULT.json"
WEATHER_MODULE = WEATHER_ROOT / "control/weather/madis_ldm_queue_native_a19b_v2.py"
V2_VALIDATOR = WEATHER_ROOT / "control/jobs/validate_madis_ldm_a19b_v2.py"


def run(*args: str, cwd: Path | None = None, timeout: int = 20) -> dict:
    try:
        cp = subprocess.run(
            args,
            cwd=cwd or ROOT,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return {
            "returncode": cp.returncode,
            "stdout": cp.stdout[-12000:],
            "stderr": cp.stderr[-6000:],
        }
    except Exception as exc:
        return {
            "returncode": None,
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}",
        }


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {"_non_object": True}
    except Exception as exc:
        return {"_read_error": f"{type(exc).__name__}: {exc}"}


out: dict = {
    "task": "WEATHER-A19B-V2-CLOCK-GATE-DIAGNOSE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "economic_conclusion": "NO_PROVEN_EDGE",
}

out["result_028_present"] = RESULT_028.is_file()
if RESULT_028.is_file():
    out["result_028"] = read_json(RESULT_028)

out["main_head"] = run("git", "rev-parse", "HEAD", cwd=ROOT)
out["weather_branch"] = run("git", "branch", "--show-current", cwd=WEATHER_ROOT)
out["weather_head"] = run("git", "rev-parse", "HEAD", cwd=WEATHER_ROOT)
out["weather_tracked_status"] = run(
    "git", "status", "--porcelain", "--untracked-files=no", cwd=WEATHER_ROOT
)

out["clock_tools"] = {
    "chronyc": shutil.which("chronyc"),
    "timedatectl": shutil.which("timedatectl"),
}
if shutil.which("chronyc"):
    out["chronyc_tracking"] = run("chronyc", "tracking", "-n", cwd=WEATHER_ROOT)
else:
    out["chronyc_tracking"] = {"status": "NOT_INSTALLED"}
if shutil.which("timedatectl"):
    out["timedatectl_ntp"] = run(
        "timedatectl", "show", "-p", "NTPSynchronized", "--value", cwd=WEATHER_ROOT
    )
    out["timedatectl_timesync_status"] = run(
        "timedatectl", "timesync-status", "--no-pager", cwd=WEATHER_ROOT
    )
else:
    out["timedatectl_ntp"] = {"status": "NOT_AVAILABLE"}

if WEATHER_MODULE.is_file():
    try:
        spec = importlib.util.spec_from_file_location("a19b_v2_clock_diag", WEATHER_MODULE)
        if spec is None or spec.loader is None:
            raise RuntimeError("module_spec_unavailable")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        out["module_clock_health"] = mod.clock_health()
    except Exception as exc:
        out["module_clock_health"] = {"error": f"{type(exc).__name__}: {exc}"}
else:
    out["module_clock_health"] = {"error": "WEATHER_MODULE_MISSING"}

out["v2_validator_present"] = V2_VALIDATOR.is_file()
out["diagnosis"] = "INSPECT_RETURNED_EVIDENCE"
print(json.dumps(out, indent=2, sort_keys=True))
