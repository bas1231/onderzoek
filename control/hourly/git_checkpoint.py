from __future__ import annotations

import fnmatch
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

ALLOW = (
    "hourly-reports/hourly-*.md",
    "knowledge/candidates/*.json",
    "knowledge/candidates/protocols/*.json",
    "knowledge/candidates/protocols/**/*.json",
    "knowledge/recon/watchlist.json",
    "knowledge/recon/opportunity_graph.json",
    "knowledge/research_os/*.json",
    "knowledge/runs/hourly-*.json",
    "knowledge/runs/twc-revision-summary-latest.json",
)

DENY_PREFIXES = (
    "knowledge/raw/",
    "knowledge/documents/",
    "knowledge/runs/source_sweeps/",
    "knowledge/runs/agent_packets/",
    "knowledge/runs/edge_hunter/",
)

STATUS_PATH = (
    Path.home()
    / ".local/state/prediction-research/git-checkpoint-latest.json"
)


def git(
    *args: str,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
        env=env,
    )


def matches_allow(path: str) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in ALLOW)


def denied(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in DENY_PREFIXES)


def write_status(status: str, **extra) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        **extra,
    }
    STATUS_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )


def fail(reason: str, code: int = 1) -> int:
    write_status("FAIL_CLOSED", reason=reason)
    print("GIT_CHECKPOINT_FAIL_CLOSED", reason)
    return code


def staged_paths() -> list[str]:
    return [
        path
        for path in git("diff", "--cached", "--name-only").stdout.splitlines()
        if path
    ]


def build_checkpoint_commit(
    *,
    base_head: str,
    candidates: list[str],
    stamp: str,
) -> tuple[str | None, list[str], str | None]:
    """Build a checkpoint commit without touching the caller's real index.

    A temporary index starts from HEAD, stages only checkpoint-owned paths, and
    is converted into a commit object. HEAD is not moved here. This lets an
    unrelated process/session keep staged work in the real index.
    """
    with tempfile.TemporaryDirectory(prefix="prediction-git-checkpoint-") as td:
        index_path = Path(td) / "index"
        env = os.environ.copy()
        env["GIT_INDEX_FILE"] = str(index_path)

        read_tree = git("read-tree", base_head, check=False, env=env)
        if read_tree.returncode != 0:
            return None, [], "temporary index read-tree failed"

        for path in candidates:
            p = ROOT / path
            if p.exists():
                added = git("add", "--", path, check=False, env=env)
                if added.returncode != 0:
                    return None, [], f"temporary index git add failed: {path}"

        staged = [
            path
            for path in git(
                "diff",
                "--cached",
                "--name-only",
                check=False,
                env=env,
            ).stdout.splitlines()
            if path
        ]

        invalid = [
            path
            for path in staged
            if denied(path) or not matches_allow(path)
        ]
        if invalid:
            return (
                None,
                staged,
                "publisher staged forbidden paths: " + ", ".join(invalid),
            )

        if not staged:
            return None, [], None

        for path in staged:
            if not path.endswith(".json"):
                continue
            try:
                json.loads((ROOT / path).read_text())
            except Exception as exc:
                return None, staged, f"invalid JSON {path}: {exc}"

        tree = git("write-tree", check=False, env=env)
        if tree.returncode != 0:
            return None, staged, "temporary index write-tree failed"

        message = f"research(checkpoint): durable Director state {stamp}"
        commit = git(
            "commit-tree",
            tree.stdout.strip(),
            "-p",
            base_head,
            "-m",
            message,
            check=False,
            env=env,
        )
        if commit.returncode != 0:
            return None, staged, "git commit-tree failed"

        return commit.stdout.strip(), staged, None


def restore_real_index_for_checkpoint_paths(paths: list[str]) -> bool:
    """Make checkpoint-owned real-index entries match the new HEAD only.

    The caller must have verified that none of these paths were staged before
    the checkpoint. Unrelated staged entries are deliberately untouched.
    """
    for path in paths:
        reset = git("reset", "-q", "HEAD", "--", path, check=False)
        if reset.returncode != 0:
            return False
    return True


def main() -> int:
    branch = git("branch", "--show-current").stdout.strip()
    if branch != "main":
        return fail(f"unexpected branch: {branch!r}")

    fetch = git("fetch", "origin", "main", check=False)
    if fetch.returncode != 0:
        return fail("git fetch origin main failed")

    local_before = git("rev-parse", "HEAD").stdout.strip()
    remote_before = git("rev-parse", "origin/main").stdout.strip()

    if local_before != remote_before:
        return fail(
            "local HEAD differs from origin/main; manual reconciliation required"
        )

    pre_staged = staged_paths()
    pre_staged_patch = git("diff", "--cached", "--binary").stdout

    status = git(
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    ).stdout.splitlines()

    candidates: list[str] = []

    for line in status:
        if not line:
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if denied(path):
            continue
        if matches_allow(path):
            candidates.append(path)

    candidates = sorted(set(candidates))

    overlap = sorted(set(pre_staged).intersection(candidates))
    if overlap:
        return fail(
            "checkpoint candidates were already staged before checkpoint: "
            + ", ".join(overlap)
        )

    if not candidates:
        write_status(
            "NO_CHANGES",
            head=local_before,
            candidate_count=0,
            preserved_staged_count=len(pre_staged),
        )
        print("GIT_CHECKPOINT_NO_CHANGES")
        return 0

    stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    new_head, staged, build_error = build_checkpoint_commit(
        base_head=local_before,
        candidates=candidates,
        stamp=stamp,
    )

    if build_error:
        return fail(build_error)

    if not staged or not new_head:
        write_status(
            "NO_CHANGES",
            head=local_before,
            candidate_count=len(candidates),
            preserved_staged_count=len(pre_staged),
        )
        print("GIT_CHECKPOINT_NO_CHANGES")
        return 0

    fetch2 = git("fetch", "origin", "main", check=False)
    if fetch2.returncode != 0:
        return fail("second fetch failed; checkpoint commit object not published")

    remote_after = git("rev-parse", "origin/main").stdout.strip()

    if remote_after != local_before:
        return fail(
            "origin/main changed during checkpoint; checkpoint commit object "
            "not attached to local main"
        )

    update = git(
        "update-ref",
        "refs/heads/main",
        new_head,
        local_before,
        check=False,
    )
    if update.returncode != 0:
        return fail("failed to attach checkpoint commit to local main")

    if not restore_real_index_for_checkpoint_paths(staged):
        git("update-ref", "refs/heads/main", local_before, new_head, check=False)
        restore_real_index_for_checkpoint_paths(staged)
        return fail("failed to refresh checkpoint paths in real index")

    post_staged_patch = git("diff", "--cached", "--binary").stdout
    if post_staged_patch != pre_staged_patch:
        git("update-ref", "refs/heads/main", local_before, new_head, check=False)
        restore_real_index_for_checkpoint_paths(staged)
        return fail("pre-existing staged state changed; checkpoint rolled back")

    push = git("push", "origin", "main", check=False)

    if push.returncode != 0:
        return fail(
            "push failed; checkpoint committed locally but not pushed"
        )

    write_status(
        "PUBLISHED",
        previous_head=local_before,
        head=new_head,
        files=staged,
        file_count=len(staged),
        preserved_staged_count=len(pre_staged),
    )

    print("GIT_CHECKPOINT_PUBLISHED", new_head)
    print("GIT_CHECKPOINT_FILE_COUNT", len(staged))
    print("GIT_CHECKPOINT_PRESERVED_STAGED_COUNT", len(pre_staged))

    for path in staged:
        print("GIT_CHECKPOINT_FILE", path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
