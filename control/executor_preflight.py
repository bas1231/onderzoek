from __future__ import annotations

import json
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
    - local-ahead history may only be published by a normal push;
    - true divergence blocks execution;
    - no reset, rebase, stash, or force operation is ever used.
    """
    root = root.resolve()

    branch = _git(root, "branch", "--show-current")
    if branch.returncode != 0:
        return {"ok": False, "reason": "BRANCH_READ_FAILED", "stderr": branch.stderr[-4000:]}

    branch_name = branch.stdout.strip()
    if branch_name != "main":
        return {"ok": False, "reason": "NOT_MAIN_BRANCH", "branch": branch_name}

    dirty = _git(root, "status", "--porcelain", "--untracked-files=no")
    if dirty.returncode != 0:
        return {"ok": False, "reason": "TRACKED_STATUS_FAILED", "stderr": dirty.stderr[-4000:]}
    if dirty.stdout.strip():
        return {"ok": False, "reason": "TRACKED_WORKTREE_DIRTY", "detail": dirty.stdout[-4000:]}

    fetch = _git(root, "fetch", "origin", "main")
    if fetch.returncode != 0:
        return {"ok": False, "reason": "FETCH_ORIGIN_MAIN_FAILED", "stderr": fetch.stderr[-4000:]}

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
        return {"ok": True, "status": "ALREADY_CURRENT", "head": local_sha}

    local_is_ancestor = _git(root, "merge-base", "--is-ancestor", "HEAD", "origin/main")
    if local_is_ancestor.returncode == 0:
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
        return {"ok": True, "status": "FAST_FORWARDED", "before": local_sha, "head": after_sha}

    remote_is_ancestor = _git(root, "merge-base", "--is-ancestor", "origin/main", "HEAD")
    if remote_is_ancestor.returncode == 0:
        pushed = _git(root, "push", "origin", "HEAD:main")
        if pushed.returncode != 0:
            return {
                "ok": False,
                "reason": "LOCAL_AHEAD_PUSH_FAILED",
                "head": local_sha,
                "origin_main": remote_sha,
                "stderr": pushed.stderr[-4000:],
            }
        refresh = _git(root, "fetch", "origin", "main")
        remote_after = _git(root, "rev-parse", "origin/main")
        remote_after_sha = remote_after.stdout.strip() if remote_after.returncode == 0 else ""
        if refresh.returncode != 0 or remote_after.returncode != 0 or remote_after_sha != local_sha:
            return {
                "ok": False,
                "reason": "POST_PUSH_REMOTE_MISMATCH",
                "head": local_sha,
                "origin_main": remote_after_sha,
            }
        return {"ok": True, "status": "LOCAL_AHEAD_PUBLISHED", "head": local_sha}

    return {
        "ok": False,
        "reason": "DIVERGED_HISTORY",
        "head": local_sha,
        "origin_main": remote_sha,
    }


def _task_support_script_rel(task_obj: dict[str, Any]) -> Path | None:
    """Return the repository-relative support script for Python-like tasks."""
    if task_obj.get("operation") not in {"python", "health_check"}:
        return None
    command = task_obj.get("command")
    if not isinstance(command, list) or len(command) < 2 or not isinstance(command[1], str):
        return Path("__INVALID_COMMAND_SCRIPT__")
    rel = Path(command[1])
    if rel.is_absolute() or ".." in rel.parts:
        return Path("__UNSAFE_COMMAND_SCRIPT__")
    return rel


def task_provenance_in_head(root: Path, task_file: Path) -> dict[str, Any]:
    """Prove the exact pending task and its executable prerequisite are immutable.

    Seeing a task file on disk is insufficient. We require:
    - the task path exists in HEAD;
    - the latest commit that changed the task is an ancestor of HEAD;
    - the task blob at that commit equals the blob in HEAD;
    - for Python/health-check tasks, the referenced support script already
      existed in that same task commit;
    - the support-script blob at the task commit equals the one in HEAD.

    The last two invariants prevent an invalid task from becoming executable
    later merely because somebody subsequently added or changed its script.
    """
    root = root.resolve()
    try:
        rel = task_file.resolve().relative_to(root).as_posix()
    except ValueError:
        return {"ok": False, "reason": "TASK_PATH_ESCAPES_REPOSITORY"}

    head = _git(root, "rev-parse", "HEAD")
    if head.returncode != 0:
        return {"ok": False, "reason": "EXECUTION_HEAD_READ_FAILED", "stderr": head.stderr[-2000:]}
    execution_commit = head.stdout.strip()

    head_blob = _git(root, "rev-parse", f"HEAD:{rel}")
    if head_blob.returncode != 0:
        return {
            "ok": False,
            "reason": "TASK_NOT_TRACKED_IN_EXECUTION_HEAD",
            "task_path": rel,
            "execution_commit": execution_commit,
        }

    latest = _git(root, "log", "-1", "--format=%H", "HEAD", "--", rel)
    task_commit = latest.stdout.strip() if latest.returncode == 0 else ""
    if not task_commit:
        return {
            "ok": False,
            "reason": "TASK_COMMIT_NOT_FOUND",
            "task_path": rel,
            "execution_commit": execution_commit,
        }

    ancestor = _git(root, "merge-base", "--is-ancestor", task_commit, execution_commit)
    if ancestor.returncode != 0:
        return {
            "ok": False,
            "reason": "TASK_COMMIT_NOT_IN_EXECUTION_HISTORY",
            "task_path": rel,
            "task_commit": task_commit,
            "execution_commit": execution_commit,
        }

    task_blob = _git(root, "rev-parse", f"{task_commit}:{rel}")
    if task_blob.returncode != 0:
        return {
            "ok": False,
            "reason": "TASK_BLOB_NOT_FOUND_AT_TASK_COMMIT",
            "task_path": rel,
            "task_commit": task_commit,
            "execution_commit": execution_commit,
        }

    task_blob_sha = task_blob.stdout.strip()
    head_blob_sha = head_blob.stdout.strip()
    if task_blob_sha != head_blob_sha:
        return {
            "ok": False,
            "reason": "TASK_BLOB_CHANGED_AFTER_TASK_COMMIT",
            "task_path": rel,
            "task_commit": task_commit,
            "execution_commit": execution_commit,
            "task_blob": task_blob_sha,
            "execution_blob": head_blob_sha,
        }

    try:
        task_obj = json.loads(task_file.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "ok": False,
            "reason": "TASK_JSON_READ_FAILED",
            "task_path": rel,
            "task_commit": task_commit,
            "execution_commit": execution_commit,
            "detail": f"{type(exc).__name__}: {exc}",
        }
    if not isinstance(task_obj, dict):
        return {
            "ok": False,
            "reason": "TASK_JSON_NOT_OBJECT",
            "task_path": rel,
            "task_commit": task_commit,
            "execution_commit": execution_commit,
        }

    script_rel = _task_support_script_rel(task_obj)
    support_provenance: dict[str, Any] | None = None
    if script_rel is not None:
        script_text = script_rel.as_posix()
        if script_text == "__INVALID_COMMAND_SCRIPT__":
            return {
                "ok": False,
                "reason": "COMMAND_SCRIPT_MISSING",
                "task_path": rel,
                "task_commit": task_commit,
                "execution_commit": execution_commit,
            }
        if script_text == "__UNSAFE_COMMAND_SCRIPT__":
            return {
                "ok": False,
                "reason": "UNSAFE_SCRIPT_PATH",
                "task_path": rel,
                "task_commit": task_commit,
                "execution_commit": execution_commit,
            }

        at_task = _git(root, "rev-parse", f"{task_commit}:{script_text}")
        if at_task.returncode != 0:
            return {
                "ok": False,
                "reason": "SUPPORT_SCRIPT_NOT_IN_TASK_COMMIT",
                "task_path": rel,
                "script": script_text,
                "task_commit": task_commit,
                "execution_commit": execution_commit,
            }

        at_head = _git(root, "rev-parse", f"HEAD:{script_text}")
        if at_head.returncode != 0:
            return {
                "ok": False,
                "reason": "SUPPORT_SCRIPT_NOT_TRACKED_IN_EXECUTION_HEAD",
                "task_path": rel,
                "script": script_text,
                "task_commit": task_commit,
                "execution_commit": execution_commit,
            }

        task_script_blob = at_task.stdout.strip()
        head_script_blob = at_head.stdout.strip()
        if task_script_blob != head_script_blob:
            return {
                "ok": False,
                "reason": "SUPPORT_SCRIPT_CHANGED_AFTER_TASK_COMMIT",
                "task_path": rel,
                "script": script_text,
                "task_commit": task_commit,
                "execution_commit": execution_commit,
                "task_script_blob": task_script_blob,
                "execution_script_blob": head_script_blob,
            }

        support_provenance = {
            "status": "SUPPORT_SCRIPT_BOUND_TO_TASK_COMMIT",
            "script": script_text,
            "script_blob": task_script_blob,
        }

    return {
        "ok": True,
        "status": "TASK_COMMIT_PROVEN",
        "task_path": rel,
        "task_commit": task_commit,
        "task_blob": task_blob_sha,
        "execution_commit": execution_commit,
        "relationship": "equal" if task_commit == execution_commit else "ancestor",
        "support_provenance": support_provenance,
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
        return {"ok": False, "reason": "SUPPORT_SCRIPT_MISSING_ON_DISK", "script": rel.as_posix()}

    tracked = _git(root, "cat-file", "-e", f"HEAD:{rel.as_posix()}")
    if tracked.returncode != 0:
        return {"ok": False, "reason": "SUPPORT_SCRIPT_NOT_TRACKED_IN_HEAD", "script": rel.as_posix()}

    return {"ok": True, "status": "SUPPORT_SCRIPT_TRACKED", "script": rel.as_posix()}
