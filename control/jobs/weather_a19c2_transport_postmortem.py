#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

HOME = Path.home()
TASK_ID = "WEATHER-A19C2-TRANSPORT-RECOVER-028"
TARGET = "weather_clock_transport_diag_a19c2.py"
VENV_PYTHON = HOME / "prediction_research" / ".venv" / "bin" / "python"


def run(*args: str, cwd: Path | None = None, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=timeout)


def safe_json(path: Path):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value
    except Exception as exc:
        return {"_parse_error": f"{type(exc).__name__}: {exc}"}


def git_meta(path: Path) -> dict:
    cp = run("git", "-C", str(path), "rev-parse", "--show-toplevel")
    if cp.returncode != 0:
        return {"is_git_repo": False}
    root = Path(cp.stdout.strip()).resolve()
    head = run("git", "rev-parse", "HEAD", cwd=root)
    branch = run("git", "branch", "--show-current", cwd=root)
    status = run("git", "status", "--porcelain", cwd=root)
    return {
        "is_git_repo": True,
        "root": str(root),
        "head": head.stdout.strip() if head.returncode == 0 else None,
        "branch": branch.stdout.strip() if branch.returncode == 0 else None,
        "tracked_dirty": bool(status.stdout.strip()),
    }


roots = sorted(p.resolve() for p in HOME.glob("prediction_research*") if p.is_dir())
result = {
    "task": "WEATHER-A19C2-TRANSPORT-POSTMORTEM",
    "target_task_id": TASK_ID,
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "openai_api": False,
    "venv_python": {
        "path": str(VENV_PYTHON),
        "exists": VENV_PYTHON.is_file(),
        "executable": VENV_PYTHON.is_file() and bool(VENV_PYTHON.stat().st_mode & 0o111),
    },
    "repositories": [],
    "result_candidates": [],
    "task_candidates": [],
    "lifecycle_candidates": [],
    "a19c2_sources": [],
}

for root in roots:
    meta = git_meta(root)
    result["repositories"].append(meta)

    result_path = root / "control" / "results" / TASK_ID / "RESULT.json"
    if result_path.is_file():
        result["result_candidates"].append({
            "path": str(result_path),
            "sha256": hashlib.sha256(result_path.read_bytes()).hexdigest(),
            "content": safe_json(result_path),
        })

    tasks_root = root / "control" / "tasks"
    if tasks_root.is_dir():
        for state in ("pending", "running", "completed", "failed"):
            for path in sorted((tasks_root / state).glob(f"*{TASK_ID}*")) if (tasks_root / state).is_dir() else []:
                result["task_candidates"].append({
                    "state": state,
                    "path": str(path),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "content": safe_json(path),
                })

    lifecycle_root = root / "control" / "lifecycle"
    if lifecycle_root.is_dir():
        for path in sorted(lifecycle_root.glob(f"*{TASK_ID}*")):
            if path.is_file():
                result["lifecycle_candidates"].append({
                    "path": str(path),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "content": safe_json(path),
                })

    source = root / "control" / "jobs" / TARGET
    if source.is_file():
        repo_root = Path(meta.get("root")) if meta.get("root") else root
        try:
            rel = source.relative_to(repo_root).as_posix()
        except ValueError:
            rel = None
        tracked = False
        clean = False
        if rel:
            tracked_cp = run("git", "ls-files", "--error-unmatch", "--", rel, cwd=repo_root)
            status_cp = run("git", "status", "--porcelain", "--", rel, cwd=repo_root)
            tracked = tracked_cp.returncode == 0
            clean = status_cp.returncode == 0 and not status_cp.stdout.strip()
        result["a19c2_sources"].append({
            "path": str(source),
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "repo_root": str(repo_root),
            "relative_path": rel,
            "tracked": tracked,
            "clean": clean,
            "git_head": meta.get("head"),
            "git_branch": meta.get("branch"),
        })

# Fail closed on ambiguity; this is a diagnostic only and never executes source.
if result["result_candidates"]:
    status = "POSTMORTEM_RESULT_FOUND"
    next_gate = "REVIEW_028_RESULT_AND_REPAIR_EXACT_FAILURE"
elif not result["venv_python"]["exists"]:
    status = "POSTMORTEM_VENV_MISSING_CONFIRMED"
    next_gate = "RESTORE_EXISTING_LOCAL_VENV_OR_ADAPT_RUNNER_WITHOUT_INSTALL"
elif not result["a19c2_sources"]:
    status = "POSTMORTEM_A19C2_SOURCE_MISSING"
    next_gate = "RECOVER_A19C2_SOURCE_PROVENANCE"
else:
    status = "POSTMORTEM_PROVENANCE_INCOMPLETE"
    next_gate = "INSPECT_LOCAL_TASK_AND_SOURCE_STATE"

result["status"] = status
result["next_gate"] = next_gate
print(json.dumps(result, indent=2, sort_keys=True))
