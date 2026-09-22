from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )


def sync_main_fail_closed(root: Path) -> dict[str, Any]:
    """Safely synchronize an executor checkout with origin/main.

    Invariants:
    - tracked local changes block synchronization;
    - only a clean checkout on branch `main` is eligible;
    - remote history may only be incorporated by fast-forward;
    - no reset, rebase, stash, or force operation is ever used.
    """
    root = root.resolve()

    branch = _git(root, "branch", "--show-current")
    if branch.returncode != 0:
        return {
            "ok": False,
            "reason": "BRANCH_READ_FAILED",
            "stderr": branch.stderr[-4000:],
        }

    branch_name = branch.stdout.strip()
    if branch_name != "main":
        return {
            "ok": False,
            "reason": "NOT_MAIN_BRANCH",
            "branch": branch_name,
        }

    dirty = _git(root, "status", "--porcelain", "--untracked-files=no")
    if dirty.returncode != 0:
        return {
            "ok": False,
            "reason": "TRACKED_STATUS_FAILED",
            "stderr": dirty.stderr[-4000:],
        }
    if dirty.stdout.strip():
        return {
            "ok": False,
            "reason": "TRACKED_WORKTREE_DIRTY",
            "detail": dirty.stdout[-4000:],
        }

    fetch = _git(root, "fetch", "origin", "main")
    if fetch.returncode != 0:
        return {
            "ok": False,
            "reason": "FETCH_ORIGIN_MAIN_FAILED",
            "stderr": fetch.stderr[-4000:],
        }

    local = _git(root, "rev-parse", "HEAD")
    remote = _git(root, "rev-parse", "origin/main")
    if local.returncode != 0 or remote.returncode != 0:
        return {
            "ok": False,
            "reason": "REV_PARSE_FAILED",
            "local_stderr": local.stderr[-2000:],
            "remote_stderr": remote.stderr[-2000:],
        }

    local_sha = local.stdout.strip()
    remote_sha = remote.stdout.strip()
    if local_sha == remote_sha:
        return {
            "ok": True,
            "status": "ALREADY_CURRENT",
            "head": local_sha,
        }

    ancestor = _git(root, "merge-base", "--is-ancestor", "HEAD", "origin/main")
    if ancestor.returncode != 0:
        return {
            "ok": False,
            "reason": "NON_FAST_FORWARD_OR_DIVERGED",
            "head": local_sha,
            "origin_main": remote_sha,
        }

    ff = _git(root, "merge", "--ff-only", "origin/main")
    if ff.returncode != 0:
        return {
            "ok": False,
            "reason": "FAST_FORWARD_FAILED",
            "head": local_sha,
            "origin_main": remote_sha,
            "stderr": ff.stderr[-4000:],
        }

    after = _git(root, "rev-parse", "HEAD")
    after_sha = after.stdout.strip() if after.returncode == 0 else ""
    if after.returncode != 0 or after_sha != remote_sha:
        return {
            "ok": False,
            "reason": "POST_FAST_FORWARD_HEAD_MISMATCH",
            "head": after_sha,
            "origin_main": remote_sha,
        }

    return {
        "ok": True,
        "status": "FAST_FORWARDED",
        "before": local_sha,
        "head": after_sha,
    }


def support_script_in_head(root: Path, task: Any) -> dict[str, Any]:
    """Prove a Python task's support script exists and is tracked in HEAD."""
    if getattr(task, "operation", None) not in {"python", "health_check"}:
        return {"ok": True, "status": "NOT_APPLICABLE"}

    command = list(getattr(task, "command", []) or [])
    if len(command) < 2:
        return {"ok": False, "reason": "COMMAND_SCRIPT_MISSING"}

    rel = Path(command[1])
    if rel.is_absolute() or ".." in rel.parts:
        return {"ok": False, "reason": "UNSAFE_SCRIPT_PATH"}

    script = (root / rel).resolve()
    root_resolved = root.resolve()
    if root_resolved not in script.parents:
        return {"ok": False, "reason": "SCRIPT_ESCAPES_REPOSITORY"}

    if not script.is_file():
        return {
            "ok": False,
            "reason": "SUPPORT_SCRIPT_MISSING_ON_DISK",
            "script": rel.as_posix(),
        }

    tracked = _git(root, "cat-file", "-e", f"HEAD:{rel.as_posix()}")
    if tracked.returncode != 0:
        return {
            "ok": False,
            "reason": "SUPPORT_SCRIPT_NOT_TRACKED_IN_HEAD",
            "script": rel.as_posix(),
        }

    return {
        "ok": True,
        "status": "SUPPORT_SCRIPT_TRACKED",
        "script": rel.as_posix(),
    }
