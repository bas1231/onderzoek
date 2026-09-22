#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

HOME = Path.home()
TARGET = "weather_clock_transport_diag_a19c2.py"
MAX_TEXT = 1_000_000
MAX_DANGLING_BLOBS = 1200


def run(*args: str, cwd: Path | None = None, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=timeout)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_root(path: Path) -> Path | None:
    cp = run("git", "-C", str(path), "rev-parse", "--show-toplevel", timeout=10)
    if cp.returncode != 0 or not cp.stdout.strip():
        return None
    return Path(cp.stdout.strip()).resolve()


def blob_text(repo: Path, sha: str) -> str | None:
    size = run("git", "cat-file", "-s", sha, cwd=repo, timeout=10)
    if size.returncode != 0:
        return None
    try:
        n = int(size.stdout.strip())
    except Exception:
        return None
    if n < 1 or n > MAX_TEXT:
        return None
    cp = run("git", "cat-file", "-p", sha, cwd=repo, timeout=10)
    return cp.stdout if cp.returncode == 0 else None


def looks_like_source(text: str) -> bool:
    low = text.lower()
    strong = (
        "a19c2" in low
        and "clock" in low
        and ("chrony" in low or "timedatectl" in low or "ntp" in low)
    )
    named = TARGET.lower() in low
    return strong or named


roots = sorted({
    p.resolve()
    for p in HOME.glob("prediction_research*")
    if p.is_dir()
})

out: dict = {
    "task": "WEATHER-A19C2-SOURCE-FORENSIC-030",
    "status": "DIAGNOSTIC",
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "openai_api": False,
    "searched_roots": [str(p) for p in roots],
    "exact_files": [],
    "content_candidates": [],
    "history_hits": [],
    "reflog_hits": [],
    "stash_hits": [],
    "dangling_blob_candidates": [],
    "text_reference_files": [],
}

repos: list[Path] = []
seen_repo: set[str] = set()
for root in roots:
    repo = git_root(root)
    if repo is not None and str(repo) not in seen_repo:
        repos.append(repo)
        seen_repo.add(str(repo))

    # Filesystem exact-name and content scan, limited to likely source/control locations.
    for base in (root / "control", root / "experiments"):
        if not base.is_dir():
            continue
        for path in base.rglob("*.py"):
            if not path.is_file():
                continue
            if path.name == TARGET:
                data = path.read_bytes()
                out["exact_files"].append({
                    "path": str(path.resolve()),
                    "sha256": sha256_bytes(data),
                    "repo_root": str(repo) if repo else None,
                })
            try:
                text = path.read_text(encoding="utf-8", errors="replace")[:MAX_TEXT]
            except Exception:
                continue
            if looks_like_source(text) and path.name != TARGET:
                out["content_candidates"].append({
                    "path": str(path.resolve()),
                    "sha256": sha256_bytes(path.read_bytes()),
                    "preview": text[:2500],
                })

    # Search task/result/control text for literal target references or embedded A19C2 source text.
    control = root / "control"
    if control.is_dir():
        for suffix in ("*.json", "*.md", "*.txt"):
            for path in control.rglob(suffix):
                if not path.is_file():
                    continue
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")[:MAX_TEXT]
                except Exception:
                    continue
                low = text.lower()
                if TARGET.lower() in low or ("a19c2" in low and "clock" in low and "transport" in low):
                    out["text_reference_files"].append({
                        "path": str(path.resolve()),
                        "sha256": sha256_bytes(path.read_bytes()),
                        "preview": text[:3500],
                    })
                    if len(out["text_reference_files"]) >= 40:
                        break
            if len(out["text_reference_files"]) >= 40:
                break

for repo in repos:
    # Normal reachable history across every ref.
    hist = run(
        "git", "log", "--all", "--format=%H", "--", f"control/jobs/{TARGET}",
        cwd=repo, timeout=30,
    )
    if hist.returncode == 0:
        for sha in [x.strip() for x in hist.stdout.splitlines() if x.strip()]:
            show = run("git", "show", f"{sha}:control/jobs/{TARGET}", cwd=repo, timeout=15)
            if show.returncode == 0:
                out["history_hits"].append({
                    "repo": str(repo),
                    "commit": sha,
                    "sha256": sha256_bytes(show.stdout.encode()),
                    "preview": show.stdout[:3500],
                })

    # Reflogs can reference commits that are no longer on a branch.
    reflog = run("git", "reflog", "show", "--all", "--format=%H", cwd=repo, timeout=30)
    if reflog.returncode == 0:
        seen_commits: set[str] = set()
        for sha in [x.strip() for x in reflog.stdout.splitlines() if x.strip()]:
            if sha in seen_commits:
                continue
            seen_commits.add(sha)
            exists = run("git", "cat-file", "-e", f"{sha}:control/jobs/{TARGET}", cwd=repo, timeout=5)
            if exists.returncode == 0:
                show = run("git", "show", f"{sha}:control/jobs/{TARGET}", cwd=repo, timeout=10)
                if show.returncode == 0:
                    out["reflog_hits"].append({
                        "repo": str(repo),
                        "commit": sha,
                        "sha256": sha256_bytes(show.stdout.encode()),
                        "preview": show.stdout[:3500],
                    })

    # Stashes.
    stashes = run("git", "stash", "list", "--format=%H", cwd=repo, timeout=10)
    if stashes.returncode == 0:
        for sha in [x.strip() for x in stashes.stdout.splitlines() if x.strip()]:
            show = run("git", "show", f"{sha}:control/jobs/{TARGET}", cwd=repo, timeout=10)
            if show.returncode == 0:
                out["stash_hits"].append({
                    "repo": str(repo),
                    "stash_commit": sha,
                    "sha256": sha256_bytes(show.stdout.encode()),
                    "preview": show.stdout[:3500],
                })

    # Unreachable blobs. Read-only and bounded.
    fsck = run("git", "fsck", "--full", "--no-reflogs", "--unreachable", "--no-progress", cwd=repo, timeout=90)
    blob_shas: list[str] = []
    combined = (fsck.stdout or "") + "\n" + (fsck.stderr or "")
    for line in combined.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] in {"unreachable", "dangling"} and parts[1] == "blob":
            blob_shas.append(parts[2])
            if len(blob_shas) >= MAX_DANGLING_BLOBS:
                break
    for sha in blob_shas:
        text = blob_text(repo, sha)
        if text is None or not looks_like_source(text):
            continue
        out["dangling_blob_candidates"].append({
            "repo": str(repo),
            "blob": sha,
            "sha256": sha256_bytes(text.encode()),
            "preview": text[:5000],
        })
        if len(out["dangling_blob_candidates"]) >= 20:
            break

recoverable = (
    out["exact_files"]
    + out["history_hits"]
    + out["reflog_hits"]
    + out["stash_hits"]
    + out["dangling_blob_candidates"]
)
unique_hashes = sorted({str(x.get("sha256")) for x in recoverable if x.get("sha256")})

if len(unique_hashes) == 1 and recoverable:
    out["status"] = "EXACT_SOURCE_RECOVERABLE"
    out["next_gate"] = "RECOVER_SINGLE_PROVENANCE_SOURCE_AND_VALIDATE"
elif len(unique_hashes) > 1:
    out["status"] = "AMBIGUOUS_SOURCE"
    out["next_gate"] = "RESOLVE_A19C2_SOURCE_HASH_AMBIGUITY"
else:
    out["status"] = "SOURCE_NOT_RECOVERED"
    out["next_gate"] = "RECONSTRUCT_ONLY_FROM_DOCUMENTED_REQUIREMENTS_OR_RETIRE_A19C2_TRANSPORT_ARTIFACT"

out["recoverable_unique_sha256"] = unique_hashes
print(json.dumps(out, indent=2, sort_keys=True))
