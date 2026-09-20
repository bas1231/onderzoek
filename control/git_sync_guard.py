from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import subprocess
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class GitSyncState:
    safe_to_write: bool
    status: str
    branch: str | None
    local_head: str | None
    remote_head: str | None
    detail: str

    def as_dict(self) -> dict:
        return asdict(self)


def _run(root: Path, args: Sequence[str]):
    return subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )


def inspect_remote_write_safety(
    *,
    root: Path = ROOT,
    fetch: bool = True,
    required_branch: str = "main",
) -> GitSyncState:
    """Determine whether repository writes are safe relative to origin/main.

    The guard never pulls, merges or rebases. It may fetch the remote ref and
    then classifies local/remote ancestry. Only an exact sync is safe for
    starting another repository-mutating task. LOCAL_AHEAD is deliberately
    blocked too: it commonly means an earlier push failed and must be resolved
    before the worker creates more local commits.
    """
    try:
        branch_probe = _run(
            root,
            ["symbolic-ref", "--quiet", "--short", "HEAD"],
        )
    except Exception as exc:
        return GitSyncState(
            False,
            "PROBE_ERROR",
            None,
            None,
            None,
            f"{type(exc).__name__}: {exc}",
        )

    if branch_probe.returncode != 0:
        return GitSyncState(
            False,
            "DETACHED_OR_UNKNOWN_BRANCH",
            None,
            None,
            None,
            branch_probe.stderr.strip()
            or "HEAD is not on a named branch",
        )

    branch = branch_probe.stdout.strip()
    if branch != required_branch:
        return GitSyncState(
            False,
            "WRONG_BRANCH",
            branch,
            None,
            None,
            f"required branch is {required_branch}",
        )

    if fetch:
        fetched = _run(
            root,
            ["fetch", "--quiet", "origin", required_branch],
        )
        if fetched.returncode != 0:
            return GitSyncState(
                False,
                "FETCH_FAILED",
                branch,
                None,
                None,
                fetched.stderr.strip() or "git fetch failed",
            )

    local_probe = _run(root, ["rev-parse", "HEAD"])
    remote_probe = _run(
        root,
        ["rev-parse", f"origin/{required_branch}"],
    )

    if local_probe.returncode != 0 or remote_probe.returncode != 0:
        detail = "; ".join(
            item
            for item in (
                local_probe.stderr.strip(),
                remote_probe.stderr.strip(),
            )
            if item
        ) or "unable to resolve local/remote head"
        return GitSyncState(
            False,
            "HEAD_RESOLUTION_FAILED",
            branch,
            None,
            None,
            detail,
        )

    local_head = local_probe.stdout.strip()
    remote_head = remote_probe.stdout.strip()

    if local_head == remote_head:
        return GitSyncState(
            True,
            "SYNCED",
            branch,
            local_head,
            remote_head,
            f"local HEAD equals origin/{required_branch}",
        )

    local_is_ancestor = _run(
        root,
        ["merge-base", "--is-ancestor", local_head, remote_head],
    )
    if local_is_ancestor.returncode == 0:
        return GitSyncState(
            False,
            "LOCAL_BEHIND",
            branch,
            local_head,
            remote_head,
            f"origin/{required_branch} contains commits not present locally",
        )

    remote_is_ancestor = _run(
        root,
        ["merge-base", "--is-ancestor", remote_head, local_head],
    )
    if remote_is_ancestor.returncode == 0:
        return GitSyncState(
            False,
            "LOCAL_AHEAD",
            branch,
            local_head,
            remote_head,
            f"local HEAD contains unpushed commits on top of origin/{required_branch}",
        )

    return GitSyncState(
        False,
        "DIVERGED",
        branch,
        local_head,
        remote_head,
        f"local HEAD and origin/{required_branch} have both advanced",
    )


def require_remote_write_safety(
    *,
    root: Path = ROOT,
    fetch: bool = True,
    required_branch: str = "main",
) -> GitSyncState:
    state = inspect_remote_write_safety(
        root=root,
        fetch=fetch,
        required_branch=required_branch,
    )
    if not state.safe_to_write:
        raise RuntimeError(
            "git sync guard blocked write: "
            f"{state.status}: {state.detail}"
        )
    return state
