#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

TASK_ID = "WEATHER-CLOCK-A19C-GATE-032"
ROOTS = [
    Path.home() / "prediction_research",
    Path.home() / "prediction_research_weather",
]
MAX_FILE_CHARS = 20000
MAX_MATCHES = 40


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 15) -> dict:
    try:
        cp = subprocess.run(
            cmd,
            cwd=cwd,
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
        return {"error": f"{type(exc).__name__}: {exc}"}


def read_text(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        return {
            "path": str(path),
            "bytes": path.stat().st_size,
            "content": text[-MAX_FILE_CHARS:],
            "truncated_to_tail": len(text) > MAX_FILE_CHARS,
        }
    except Exception as exc:
        return {
            "path": str(path),
            "read_error": f"{type(exc).__name__}: {exc}",
        }


def interesting_files(root: Path) -> list[Path]:
    candidates: list[Path] = []
    exact = [
        root / "control" / "results" / TASK_ID / "RESULT.json",
        root / "control" / "results" / TASK_ID / "stdout.txt",
        root / "control" / "results" / TASK_ID / "stderr.txt",
        root / "control" / "lifecycle" / f"{TASK_ID}.json",
    ]
    candidates.extend(p for p in exact if p.is_file())

    for task_state in ("pending", "running", "completed", "failed"):
        p = root / "control" / "tasks" / task_state / f"{TASK_ID}.json"
        if p.is_file():
            candidates.append(p)

    search_roots = [
        root / "control" / "results",
        root / "control" / "lifecycle",
        root / "evidence" / "weather",
        root / "control" / "jobs",
        root / "control" / "weather",
    ]
    tokens = ("a19c", "clock")
    for base in search_roots:
        if not base.is_dir():
            continue
        try:
            for p in base.rglob("*"):
                if len(candidates) >= MAX_MATCHES:
                    break
                if not p.is_file():
                    continue
                low = p.name.lower()
                if TASK_ID.lower() in low or any(t in low for t in tokens):
                    if p.suffix.lower() in {".json", ".txt", ".md", ".py", ".log"}:
                        candidates.append(p)
        except Exception:
            pass

    unique: list[Path] = []
    seen: set[str] = set()
    for p in candidates:
        key = str(p.resolve())
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique[:MAX_MATCHES]


out: dict = {
    "task": "WEATHER-CLOCK-A19C-DIAG-033",
    "target_failed_task": TASK_ID,
    "mode": "READ_ONLY_DIAGNOSTIC",
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "openai_api": False,
    "roots": {},
    "clock_runtime_inventory": {
        "chronyc_path": shutil.which("chronyc"),
        "timedatectl_path": shutil.which("timedatectl"),
    },
}

for root in ROOTS:
    key = root.name
    section: dict = {
        "exists": root.is_dir(),
        "git": {},
        "files": [],
    }
    if root.is_dir():
        section["git"]["head"] = run(["git", "rev-parse", "HEAD"], cwd=root)
        section["git"]["branch"] = run(["git", "branch", "--show-current"], cwd=root)
        section["git"]["status_tracked"] = run(
            ["git", "status", "--porcelain", "--untracked-files=no"], cwd=root
        )
        section["git"]["source_commit_032"] = run(
            ["git", "show", "--no-patch", "--format=%H%n%P%n%s", "764837e4efd2bbbe725e1148a650423fbb0dddc6"],
            cwd=root,
        )
        section["files"] = [read_text(p) for p in interesting_files(root)]
    out["roots"][key] = section

if shutil.which("chronyc"):
    out["clock_runtime_inventory"]["chronyc_tracking"] = run(
        ["chronyc", "tracking", "-n"], timeout=10
    )
if shutil.which("timedatectl"):
    out["clock_runtime_inventory"]["timedatectl_ntp"] = run(
        ["timedatectl", "show", "-p", "NTPSynchronized", "--value"], timeout=10
    )

print(json.dumps(out, indent=2, sort_keys=True))
