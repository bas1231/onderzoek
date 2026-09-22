#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys

WEATHER_ROOT = Path.home() / "prediction_research_weather"
WEATHER_MODULES = WEATHER_ROOT / "control" / "weather"


def run(*args: str, timeout: int = 10) -> dict:
    try:
        cp = subprocess.run(
            args,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return {
            "command": list(args),
            "returncode": cp.returncode,
            "stdout": cp.stdout[-8000:],
            "stderr": cp.stderr[-4000:],
        }
    except Exception as exc:
        return {
            "command": list(args),
            "returncode": None,
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}",
        }


result: dict = {
    "task": "WEATHER-A19B-V2-CLOCK-DIAGNOSTIC",
    "status": "DIAGNOSTIC_COMPLETED",
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "system_modified": False,
    "inventory": {},
}

result["inventory"]["chronyc_path"] = shutil.which("chronyc")
if shutil.which("chronyc"):
    result["inventory"]["chronyc_tracking"] = run("chronyc", "tracking", "-n")
    result["inventory"]["chronyc_sources"] = run("chronyc", "sources", "-n")
else:
    result["inventory"]["chronyc_tracking"] = {"status": "NOT_INSTALLED"}

if shutil.which("timedatectl"):
    result["inventory"]["timedatectl_sync"] = run(
        "timedatectl", "show",
        "-p", "NTPSynchronized",
        "-p", "NTP",
        "-p", "LocalRTC",
    )
else:
    result["inventory"]["timedatectl_sync"] = {"status": "NOT_AVAILABLE"}

clocksource = Path("/sys/devices/system/clocksource/clocksource0/current_clocksource")
if clocksource.is_file():
    try:
        result["inventory"]["kernel_clocksource"] = clocksource.read_text(encoding="utf-8").strip()
    except Exception as exc:
        result["inventory"]["kernel_clocksource_error"] = f"{type(exc).__name__}: {exc}"

result["inventory"]["uname"] = run("uname", "-a")

clock_health = None
if WEATHER_MODULES.is_dir():
    sys.path.insert(0, str(WEATHER_MODULES))
    try:
        import madis_ldm_ingest_a19b as a19b
        clock_health = a19b.clock_health()
    except Exception as exc:
        result["clock_health_error"] = f"{type(exc).__name__}: {exc}"
else:
    result["clock_health_error"] = "WEATHER_MODULE_PATH_MISSING"

result["clock_health"] = clock_health
eligible = bool(
    isinstance(clock_health, dict)
    and clock_health.get("evidence_clock_eligible") is True
)
result["evidence_clock_eligible"] = eligible
result["research_gate"] = (
    "CLOCK_EVIDENCE_READY"
    if eligible
    else "BLOCKED_CLOCK_EVIDENCE"
)
result["terminal_for_current_authorization"] = not eligible
result["interpretation"] = (
    "Clock evidence satisfies the current A19B-v2 evidence gate."
    if eligible
    else "Passive diagnostic completed, but clock offset/uncertainty evidence is insufficient. No system changes were attempted."
)

print(json.dumps(result, indent=2, sort_keys=True))
# A missing/insufficient clock is a research gate, not a diagnostic execution failure.
raise SystemExit(0)
