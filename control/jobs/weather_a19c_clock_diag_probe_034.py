#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

TASK_ID = "WEATHER-A19C-CLOCK-DIAG-033"
ROOTS = [
    Path.home() / "prediction_research",
    Path.home() / "prediction_research_weather",
]


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
        return {
            "command": args,
            "error": f"{type(exc).__name__}: {exc}",
        }


def read_text(path: Path, limit: int = 20000) -> str | None:
    try:
        if path.is_file():
            return path.read_text(encoding="utf-8", errors="replace")[-limit:]
    except Exception as exc:
        return f"READ_ERROR {type(exc).__name__}: {exc}"
    return None


out: dict = {
    "task": "WEATHER-A19C-CLOCK-DIAG-PROBE-034",
    "target_task": TASK_ID,
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "economic_conclusion": "NO_PROVEN_EDGE",
    "roots": {},
    "clock_runtime": {},
}

for root in ROOTS:
    entry: dict = {
        "exists": root.is_dir(),
    }
    if root.is_dir():
        entry["git_branch"] = run(["git", "branch", "--show-current"], cwd=root, timeout=5)
        entry["git_head"] = run(["git", "rev-parse", "HEAD"], cwd=root, timeout=5)
        entry["git_status_tracked"] = run(
            ["git", "status", "--porcelain", "--untracked-files=no"], cwd=root, timeout=5
        )

        result_dir = root / "control" / "results" / TASK_ID
        entry["result_dir"] = str(result_dir)
        entry["result_dir_exists"] = result_dir.is_dir()
        if result_dir.is_dir():
            try:
                entry["result_files"] = sorted(p.name for p in result_dir.iterdir())
            except Exception as exc:
                entry["result_files_error"] = f"{type(exc).__name__}: {exc}"
            for name in ["RESULT.json", "stdout.txt", "stderr.txt", "STDOUT.txt", "STDERR.txt"]:
                text = read_text(result_dir / name)
                if text is not None:
                    entry[name] = text

        for lifecycle in [
            root / "control" / "lifecycle" / f"{TASK_ID}.json",
            root / "control" / "tasks" / "failed" / f"{TASK_ID}.json",
            root / "control" / "tasks" / "completed" / f"{TASK_ID}.json",
            root / "control" / "tasks" / "running" / f"{TASK_ID}.json",
        ]:
            text = read_text(lifecycle)
            if text is not None:
                entry.setdefault("task_artifacts", {})[str(lifecycle.relative_to(root))] = text

    out["roots"][str(root)] = entry

chronyc = shutil.which("chronyc")
out["clock_runtime"]["chronyc_path"] = chronyc
if chronyc:
    out["clock_runtime"]["chronyc_tracking"] = run([chronyc, "tracking", "-n"], timeout=5)

for command in [
    ["timedatectl", "show", "-p", "NTPSynchronized", "--value"],
    ["timedatectl", "show", "-p", "NTPSynchronized", "-p", "NTP"],
]:
    if shutil.which(command[0]):
        out["clock_runtime"][" ".join(command)] = run(command, timeout=5)

print(json.dumps(out, indent=2, sort_keys=True))
