#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

MAIN = Path.home() / "prediction_research"
WEATHER = Path.home() / "prediction_research_weather"
TASK_ID = "WEATHER-CLOCK-A19C-GATE-033"
RESULT_DIR = MAIN / "control" / "results" / TASK_ID


def run(args: list[str], cwd: Path | None = None, timeout: int = 20) -> dict:
    try:
        cp = subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=timeout)
        return {
            "returncode": cp.returncode,
            "stdout": cp.stdout[-12000:],
            "stderr": cp.stderr[-6000:],
        }
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def read_text(path: Path, limit: int = 20000) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[-limit:]
    except Exception:
        return None


def interesting_lines(path: Path) -> list[str]:
    text = read_text(path, 100000)
    if text is None:
        return []
    needles = (
        "SystemExit", "return 2", "exit(2", "raise SystemExit(2",
        "clock", "chrony", "NTPSynchronized", "next_gate", "BLOCKED",
        "A19C", "a19c", "exit_code", "returncode"
    )
    out = []
    for idx, line in enumerate(text.splitlines(), 1):
        if any(n.lower() in line.lower() for n in needles):
            out.append(f"{idx}: {line}"[:1000])
        if len(out) >= 120:
            break
    return out


result: dict = {
    "task": "WEATHER-CLOCK-A19C-DIAG-034",
    "target_failed_task": TASK_ID,
    "read_only": True,
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "economic_conclusion": "NO_PROVEN_EDGE",
}

result["main_git"] = {
    "branch": run(["git", "branch", "--show-current"], MAIN),
    "head": run(["git", "rev-parse", "HEAD"], MAIN),
    "tracked_status": run(["git", "status", "--porcelain", "--untracked-files=no"], MAIN),
}
result["weather_git"] = {
    "branch": run(["git", "branch", "--show-current"], WEATHER),
    "head": run(["git", "rev-parse", "HEAD"], WEATHER),
    "tracked_status": run(["git", "status", "--porcelain", "--untracked-files=no"], WEATHER),
}

result_files = []
if RESULT_DIR.is_dir():
    for path in sorted(RESULT_DIR.rglob("*")):
        if path.is_file():
            entry = {
                "path": str(path),
                "size": path.stat().st_size,
            }
            if path.stat().st_size <= 250000:
                entry["tail"] = read_text(path, 20000)
            result_files.append(entry)
result["local_result_dir_exists"] = RESULT_DIR.is_dir()
result["local_result_files"] = result_files[:30]

matches = []
for base in (WEATHER / "control" / "jobs", WEATHER / "control" / "weather", WEATHER / "evidence" / "weather"):
    if not base.is_dir():
        continue
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        name = path.name.lower()
        if "a19c" in name or "clock" in name:
            matches.append({
                "path": str(path.relative_to(WEATHER)),
                "size": path.stat().st_size,
                "interesting_lines": interesting_lines(path),
            })
result["a19c_clock_files"] = matches[:80]

if shutil.which("chronyc"):
    result["chronyc"] = {
        "present": True,
        "tracking": run(["chronyc", "tracking", "-n"], WEATHER, 10),
    }
else:
    result["chronyc"] = {"present": False}

if shutil.which("timedatectl"):
    result["timedatectl"] = {
        "present": True,
        "ntp_synchronized": run(["timedatectl", "show", "-p", "NTPSynchronized", "--value"], WEATHER, 10),
    }
else:
    result["timedatectl"] = {"present": False}

print(json.dumps(result, indent=2, sort_keys=True))
