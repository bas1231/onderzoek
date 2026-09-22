#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
from datetime import datetime, timezone

MAIN_ROOT = Path.cwd()
WEATHER_ROOT = Path.home() / "prediction_research_weather"
TARGET_TASK = "WEATHER-A19C-CLOCK-GATE-030"


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 15) -> dict:
    try:
        cp = subprocess.run(
            cmd,
            cwd=cwd or MAIN_ROOT,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return {
            "command": cmd,
            "returncode": cp.returncode,
            "stdout": cp.stdout[-12000:],
            "stderr": cp.stderr[-6000:],
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": cmd,
            "returncode": 124,
            "stdout": (exc.stdout or "")[-12000:] if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "")[-6000:] if isinstance(exc.stderr, str) else "",
            "timed_out": True,
        }


def read_json(path: Path) -> dict:
    if not path.is_file():
        return {"exists": False, "path": str(path)}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return {"exists": True, "path": str(path), "parsed": obj}
    except Exception as exc:
        return {
            "exists": True,
            "path": str(path),
            "parse_error": f"{type(exc).__name__}: {exc}",
            "tail": path.read_text(encoding="utf-8", errors="replace")[-12000:],
        }


def weather_evidence_inventory() -> list[dict]:
    root = WEATHER_ROOT / "evidence" / "weather"
    if not root.is_dir():
        return []
    rows = []
    for path in sorted(root.glob("*"), key=lambda p: p.stat().st_mtime_ns, reverse=True)[:30]:
        if not path.is_file():
            continue
        row = {
            "name": path.name,
            "path": str(path),
            "size": path.stat().st_size,
            "mtime_ns": path.stat().st_mtime_ns,
        }
        if path.suffix.lower() == ".json" and path.stat().st_size <= 2_000_000:
            try:
                obj = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(obj, dict):
                    row["summary"] = {
                        key: obj.get(key)
                        for key in (
                            "task",
                            "task_id",
                            "status",
                            "next_gate",
                            "clock_gate",
                            "clock_readiness",
                            "economic_conclusion",
                            "generated_at",
                        )
                        if key in obj
                    }
            except Exception:
                pass
        rows.append(row)
    return rows


result = {
    "task": "WX-A19C-CLOCK-DIAG-031",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "target_task": TARGET_TASK,
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "economic_conclusion": "NO_PROVEN_EDGE",
}

result["main_result"] = read_json(
    MAIN_ROOT / "control" / "results" / TARGET_TASK / "RESULT.json"
)

if WEATHER_ROOT.is_dir():
    result["weather_branch"] = run(["git", "branch", "--show-current"], cwd=WEATHER_ROOT)
    result["weather_head"] = run(["git", "rev-parse", "HEAD"], cwd=WEATHER_ROOT)
    result["weather_status"] = run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=WEATHER_ROOT,
    )
    result["weather_recent_commits"] = run(
        ["git", "log", "-12", "--oneline", "--decorate"],
        cwd=WEATHER_ROOT,
    )
    result["weather_evidence"] = weather_evidence_inventory()
else:
    result["weather_root_missing"] = str(WEATHER_ROOT)

clock = {
    "chronyc_path": shutil.which("chronyc"),
    "timedatectl_path": shutil.which("timedatectl"),
}
if clock["chronyc_path"]:
    clock["chronyc_tracking"] = run([clock["chronyc_path"], "tracking", "-n"])
    clock["chronyc_sources"] = run([clock["chronyc_path"], "sources", "-v"])
if clock["timedatectl_path"]:
    clock["timedatectl_show"] = run([
        clock["timedatectl_path"],
        "show",
        "-p", "NTPSynchronized",
        "-p", "NTP",
        "-p", "TimeUSec",
    ])
result["clock_inventory"] = clock

print(json.dumps(result, indent=2, sort_keys=True))
