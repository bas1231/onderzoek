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


def _safe_rel(value: str) -> Path:
    rel = Path(value.split("::", 1)[0])
    if rel.is_absolute() or ".." in rel.parts:
        return Path("__UNSAFE_COMMAND_SCRIPT__")
    return rel


def _task_support_paths_rel(task_obj: dict[str, Any]) -> list[Path]:
    """Return explicit repository prerequisites referenced by a task.

    Python/health-check tasks bind their script. Pytest tasks bind explicit
    repository-like targets such as ``tests/x.py`` or ``tests/foo``. Pytest
    selectors after ``::`` are stripped before provenance comparison.
    """
    operation = task_obj.get("operation")
    command = task_obj.get("command")
    if not isinstance(command, list):
        return [Path("__INVALID_COMMAND_SCRIPT__")]

    if operation in {"python", "health_check"}:
        if len(command) < 2 or not isinstance(command[1], str):
            return [Path("__INVALID_COMMAND_SCRIPT__")]
        return [_safe_rel(command[1])]

    if operation != "pytest":
        return []
    if len(command) < 3:
        return [Path("__INVALID_COMMAND_SCRIPT__")]

    targets: list[Path] = []
    for item in command[3:]:
        if not isinstance(item, str) or not item or item.startswith("-"):
            continue
        raw = item.split("::", 1)[0]
        looks_repo_like = (
            raw.endswith(".py")
            or raw.startswith("tests/")
            or raw.startswith("control/")
            or raw.startswith("experiments/")
        )
        if not looks_repo_like:
            continue
        rel = _safe_rel(raw)
        if rel not in targets:
            targets.append(rel)
    return targets


def _task_support_script_rel(task_obj: dict[str, Any]) -> Path | None:
    """Backward-compatible helper used by older callers/tests."""
    paths = _task_support_paths_rel(task_obj)
    return paths[0] if paths else None


def task_provenance_in_head(root: Path, task_file: Path) -> dict[str, Any]:
    """Prove the pending task and its explicit prerequisites are immutable."""
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

    support_items: list[dict[str, str]] = []
    for support_rel in _task_support_paths_rel(task_obj):
        support_text = support_rel.as_posix()
        if support_text == "__INVALID_COMMAND_SCRIPT__":
            return {
                "ok": False,
                "reason": "COMMAND_SCRIPT_MISSING",
                "task_path": rel,
                "task_commit": task_commit,
                "execution_commit": execution_commit,
            }
        if support_text == "__UNSAFE_COMMAND_SCRIPT__":
            return {
                "ok": False,
                "reason": "UNSAFE_SCRIPT_PATH",
                "task_path": rel,
                "task_commit": task_commit,
                "execution_commit": execution_commit,
            }

        at_task = _git(root, "rev-parse", f"{task_commit}:{support_text}")
        if at_task.returncode != 0:
            return {
                "ok": False,
                "reason": "SUPPORT_SCRIPT_NOT_IN_TASK_COMMIT",
                "task_path": rel,
                "script": support_text,
                "task_commit": task_commit,
                "execution_commit": execution_commit,
            }

        at_head = _git(root, "rev-parse", f"HEAD:{support_text}")
        if at_head.returncode != 0:
            return {
                "ok": False,
                "reason": "SUPPORT_SCRIPT_NOT_TRACKED_IN_EXECUTION_HEAD",
                "task_path": rel,
                "script": support_text,
                "task_commit": task_commit,
                "execution_commit": execution_commit,
            }

        task_support_blob = at_task.stdout.strip()
        head_support_blob = at_head.stdout.strip()
        if task_support_blob != head_support_blob:
            return {
                "ok": False,
                "reason": "SUPPORT_SCRIPT_CHANGED_AFTER_TASK_COMMIT",
                "task_path": rel,
                "script": support_text,
                "task_commit": task_commit,
                "execution_commit": execution_commit,
                "task_script_blob": task_support_blob,
                "execution_script_blob": head_support_blob,
            }

        support_items.append({"script": support_text, "script_blob": task_support_blob})

    support_provenance: dict[str, Any] | None = None
    if len(support_items) == 1:
        support_provenance = {
            "status": "SUPPORT_SCRIPT_BOUND_TO_TASK_COMMIT",
            **support_items[0],
        }
    elif len(support_items) > 1:
        support_provenance = {
            "status": "SUPPORT_TARGETS_BOUND_TO_TASK_COMMIT",
            "targets": support_items,
        }
    elif task_obj.get("operation") == "pytest":
        support_provenance = {
            "status": "PYTEST_NO_EXPLICIT_REPOSITORY_TARGETS",
            "targets": [],
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
    """Prove explicit task prerequisites exist on disk and are tracked in HEAD."""
    operation = getattr(task, "operation", None)
    if operation not in {"python", "health_check", "pytest"}:
        return {"ok": True, "status": "NOT_APPLICABLE"}

    task_obj = {
        "operation": operation,
        "command": list(getattr(task, "command", []) or []),
    }
    support_paths = _task_support_paths_rel(task_obj)
    if not support_paths:
        if operation == "pytest":
            return {"ok": True, "status": "PYTEST_NO_EXPLICIT_REPOSITORY_TARGETS"}
        return {"ok": False, "reason": "COMMAND_SCRIPT_MISSING"}

    root_resolved = root.resolve()
    checked: list[str] = []
    for rel in support_paths:
        text = rel.as_posix()
        if text == "__INVALID_COMMAND_SCRIPT__":
            return {"ok": False, "reason": "COMMAND_SCRIPT_MISSING"}
        if text == "__UNSAFE_COMMAND_SCRIPT__":
            return {"ok": False, "reason": "UNSAFE_SCRIPT_PATH"}

        target = (root / rel).resolve()
        if target != root_resolved and root_resolved not in target.parents:
            return {"ok": False, "reason": "SCRIPT_ESCAPES_REPOSITORY", "script": text}
        if not target.exists():
            return {"ok": False, "reason": "SUPPORT_SCRIPT_MISSING_ON_DISK", "script": text}

        tracked = _git(root, "cat-file", "-e", f"HEAD:{text}")
        if tracked.returncode != 0:
            return {"ok": False, "reason": "SUPPORT_SCRIPT_NOT_TRACKED_IN_HEAD", "script": text}
        checked.append(text)

    if len(checked) == 1:
        return {"ok": True, "status": "SUPPORT_SCRIPT_TRACKED", "script": checked[0]}
    return {"ok": True, "status": "SUPPORT_TARGETS_TRACKED", "targets": checked}
