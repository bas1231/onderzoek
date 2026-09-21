#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

HOME = Path.home()
PYTHON = HOME / "prediction_research" / ".venv" / "bin" / "python"
TARGET = "weather_clock_transport_diag_a19c2.py"


def run(*args: str, cwd: Path | None = None, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout,
    )


def emit(payload: dict, code: int) -> None:
    payload.update({
        "economic_conclusion": "NO_PROVEN_EDGE",
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
        "openai_api": False,
    })
    print(json.dumps(payload, indent=2, sort_keys=True))
    raise SystemExit(code)


def git_root(path: Path) -> Path | None:
    cp = run("git", "-C", str(path.parent), "rev-parse", "--show-toplevel")
    if cp.returncode != 0:
        return None
    value = cp.stdout.strip()
    return Path(value).resolve() if value else None


if not PYTHON.is_file():
    emit({"status": "BLOCKED", "reason": "PREDICTION_VENV_PYTHON_MISSING"}, 2)

roots = sorted(
    p.resolve()
    for p in HOME.glob("prediction_research*")
    if p.is_dir()
)

found: list[dict] = []
for root in roots:
    direct = root / "control" / "jobs" / TARGET
    candidates = [direct] if direct.is_file() else []
    # Recall-only fallback for renamed/copied A19C2 scripts. These are inventoried
    # but never executed unless the basename is exactly TARGET.
    jobs = root / "control" / "jobs"
    if jobs.is_dir():
        for path in jobs.glob("*a19c2*.py"):
            if path.is_file() and path not in candidates:
                candidates.append(path)

    for path in candidates:
        repo = git_root(path)
        record = {
            "path": str(path.resolve()),
            "basename": path.name,
            "repo_root": str(repo) if repo else None,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "tracked": False,
            "clean": False,
            "git_head": None,
            "git_branch": None,
        }
        if repo is not None:
            try:
                rel = path.resolve().relative_to(repo).as_posix()
            except ValueError:
                rel = ""
            if rel:
                tracked = run("git", "ls-files", "--error-unmatch", "--", rel, cwd=repo)
                status = run("git", "status", "--porcelain", "--", rel, cwd=repo)
                head = run("git", "rev-parse", "HEAD", cwd=repo)
                branch = run("git", "branch", "--show-current", cwd=repo)
                record.update({
                    "relative_path": rel,
                    "tracked": tracked.returncode == 0,
                    "clean": status.returncode == 0 and not status.stdout.strip(),
                    "git_head": head.stdout.strip() if head.returncode == 0 else None,
                    "git_branch": branch.stdout.strip() if branch.returncode == 0 else None,
                    "git_status": status.stdout.strip(),
                })
        found.append(record)

exact = [r for r in found if r["basename"] == TARGET]
eligible = [r for r in exact if r["tracked"] and r["clean"] and r["repo_root"]]

if not exact:
    emit({
        "status": "BLOCKED_A19C2_SOURCE_MISSING",
        "searched_roots": [str(p) for p in roots],
        "inventory": found,
        "next_gate": "RECOVER_OR_COMMIT_ORIGINAL_A19C2_SOURCE",
    }, 3)

if not eligible:
    emit({
        "status": "BLOCKED_A19C2_SOURCE_UNSAFE",
        "inventory": found,
        "next_gate": "MAKE_ORIGINAL_A19C2_SOURCE_TRACKED_AND_CLEAN",
    }, 4)

hashes = {r["sha256"] for r in eligible}
if len(eligible) > 1 and len(hashes) > 1:
    emit({
        "status": "BLOCKED_A19C2_SOURCE_AMBIGUOUS",
        "eligible_sources": eligible,
        "next_gate": "RESOLVE_A19C2_SOURCE_PROVENANCE",
    }, 5)

# Deterministic preference: isolated Weather worktree, then lexical path.
eligible.sort(key=lambda r: ("prediction_research_weather" not in r["repo_root"], r["path"]))
source = eligible[0]
repo = Path(source["repo_root"])
rel = source["relative_path"]

try:
    proc = run(str(PYTHON), rel, cwd=repo, timeout=300)
except subprocess.TimeoutExpired as exc:
    emit({
        "status": "FAILED_A19C2_TIMEOUT",
        "source": source,
        "stdout": (exc.stdout or "")[-12000:] if isinstance(exc.stdout, str) else "",
        "stderr": (exc.stderr or "")[-6000:] if isinstance(exc.stderr, str) else "",
        "next_gate": "DIAGNOSE_A19C2_TIMEOUT",
    }, 124)

payload = {
    "status": "PASS" if proc.returncode == 0 else "FAILED_A19C2_DIAGNOSTIC",
    "source": source,
    "returncode": proc.returncode,
    "stdout": proc.stdout[-16000:],
    "stderr": proc.stderr[-8000:],
    "next_gate": "A19C2_RESULT_REVIEW" if proc.returncode == 0 else "DIAGNOSE_A19C2_RESULT",
}
emit(payload, proc.returncode)
