#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

MAIN = Path.home() / "prediction_research"
WEATHER = Path.home() / "prediction_research_weather"
TASK_ID = "WEATHER-A19C-CLOCK-GATE-033"
KEYWORDS = ("a19c", "clock", "chrony", "ntp", "uncertainty", "offset", "ldm")


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 20) -> dict:
    try:
        cp = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=timeout)
        return {
            "command": cmd,
            "returncode": cp.returncode,
            "stdout": cp.stdout[-12000:],
            "stderr": cp.stderr[-6000:],
        }
    except Exception as exc:
        return {"command": cmd, "error": f"{type(exc).__name__}: {exc}"}


def load_json(path: Path):
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value
    except Exception as exc:
        return {"_parse_error": f"{type(exc).__name__}: {exc}", "_path": str(path)}


def safe_excerpt(path: Path, max_chars: int = 16000) -> dict:
    out = {"path": str(path)}
    try:
        if not path.is_file():
            out["status"] = "MISSING"
            return out
        if path.stat().st_size > 1_000_000:
            out["status"] = "SKIPPED_TOO_LARGE"
            out["bytes"] = path.stat().st_size
            return out
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        hits = []
        for idx, line in enumerate(lines):
            if any(k in line.lower() for k in KEYWORDS) or TASK_ID.lower() in line.lower():
                lo = max(0, idx - 2)
                hi = min(len(lines), idx + 3)
                block = "\n".join(f"{n+1}: {lines[n]}" for n in range(lo, hi))
                if block not in hits:
                    hits.append(block)
            if sum(len(x) for x in hits) >= max_chars:
                break
        out["status"] = "OK"
        out["bytes"] = len(text.encode("utf-8"))
        out["matches"] = hits[:80]
    except Exception as exc:
        out["status"] = "ERROR"
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


result: dict = {
    "task": "WEATHER-A19C-READONLY-DIAG-034",
    "target_task": TASK_ID,
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "openai_api": False,
    "mutations": "NONE_READ_ONLY",
}

result["main_repo"] = {
    "exists": MAIN.is_dir(),
    "head": run(["git", "rev-parse", "HEAD"], MAIN) if MAIN.is_dir() else None,
    "branch": run(["git", "branch", "--show-current"], MAIN) if MAIN.is_dir() else None,
}
result["weather_repo"] = {
    "exists": WEATHER.is_dir(),
    "head": run(["git", "rev-parse", "HEAD"], WEATHER) if WEATHER.is_dir() else None,
    "branch": run(["git", "branch", "--show-current"], WEATHER) if WEATHER.is_dir() else None,
    "tracked_status": run(["git", "status", "--porcelain", "--untracked-files=no"], WEATHER) if WEATHER.is_dir() else None,
}

result_paths = [
    MAIN / "control" / "results" / TASK_ID / "RESULT.json",
    MAIN / "control" / "results" / TASK_ID / "STDOUT.txt",
    MAIN / "control" / "results" / TASK_ID / "STDERR.txt",
    WEATHER / "control" / "results" / TASK_ID / "RESULT.json",
    WEATHER / "evidence" / "weather" / "WEATHER-AWAY-A19B-latest.json",
]
result["known_artifacts"] = []
for p in result_paths:
    item = {"path": str(p), "exists": p.is_file()}
    if p.suffix == ".json" and p.is_file():
        item["json"] = load_json(p)
    elif p.is_file():
        item["excerpt"] = safe_excerpt(p)
    result["known_artifacts"].append(item)

candidates = []
if WEATHER.is_dir():
    for base in (WEATHER / "control" / "jobs", WEATHER / "control" / "weather", WEATHER / "evidence" / "weather"):
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(WEATHER).as_posix()
            low = rel.lower()
            if any(k in low for k in KEYWORDS):
                candidates.append(p)
result["candidate_files"] = [str(p.relative_to(WEATHER)) for p in candidates[:200]]
result["candidate_excerpts"] = [safe_excerpt(p) for p in candidates[:40] if p.suffix.lower() in {".py", ".json", ".md", ".txt", ".c", ".h"}]

clock = {
    "chronyc_path": shutil.which("chronyc"),
    "timedatectl_path": shutil.which("timedatectl"),
}
if clock["chronyc_path"]:
    clock["chronyc_tracking"] = run([clock["chronyc_path"], "tracking", "-n"], timeout=10)
if clock["timedatectl_path"]:
    clock["ntp_synchronized"] = run([clock["timedatectl_path"], "show", "-p", "NTPSynchronized", "--value"], timeout=10)
    clock["timesync_status"] = run([clock["timedatectl_path"], "timesync-status"], timeout=10)
result["clock_inventory"] = clock

print(json.dumps(result, indent=2, sort_keys=True, default=str))
