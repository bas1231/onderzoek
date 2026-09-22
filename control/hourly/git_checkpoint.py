from __future__ import annotations

import fnmatch
import json
import subprocess
import sys
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


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
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


def main() -> int:
    # Never absorb somebody else's staged work.
    if git("diff", "--cached", "--quiet", check=False).returncode != 0:
        return fail("git index was already non-empty")

    branch = git("branch", "--show-current").stdout.strip()
    if branch != "main":
        return fail(f"unexpected branch: {branch!r}")

    fetch = git("fetch", "origin", "main", check=False)
    if fetch.returncode != 0:
        return fail("git fetch origin main failed")

    local_before = git("rev-parse", "HEAD").stdout.strip()
    remote_before = git("rev-parse", "origin/main").stdout.strip()

    # Critical rule:
    # publisher never merges/rebases and never pushes unrelated local commits.
    if local_before != remote_before:
        return fail(
            "local HEAD differs from origin/main; manual reconciliation required"
        )

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

        # Handle rename notation conservatively.
        if " -> " in path:
            path = path.split(" -> ", 1)[1]

        if denied(path):
            continue

        if matches_allow(path):
            candidates.append(path)

    candidates = sorted(set(candidates))

    if not candidates:
        write_status(
            "NO_CHANGES",
            head=local_before,
            candidate_count=0,
        )
        print("GIT_CHECKPOINT_NO_CHANGES")
        return 0

    # Stage only explicit allowlisted paths.
    for path in candidates:
        p = ROOT / path
        if p.exists():
            git("add", "--", path)

    staged = [
        p
        for p in git("diff", "--cached", "--name-only").stdout.splitlines()
        if p
    ]

    # Adversarial verification of staged set.
    invalid = [
        p
        for p in staged
        if denied(p) or not matches_allow(p)
    ]

    if invalid:
        git("reset")
        return fail(
            "publisher staged forbidden paths: " + ", ".join(invalid)
        )

    if not staged:
        write_status(
            "NO_CHANGES",
            head=local_before,
            candidate_count=len(candidates),
        )
        print("GIT_CHECKPOINT_NO_CHANGES")
        return 0

    # Validate JSON before it can become durable canonical state.
    for path in staged:
        if not path.endswith(".json"):
            continue
        try:
            json.loads((ROOT / path).read_text())
        except Exception as exc:
            git("reset")
            return fail(f"invalid JSON {path}: {exc}")

    stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")

    commit = git(
        "commit",
        "-m",
        f"research(checkpoint): durable Director state {stamp}",
        check=False,
    )

    if commit.returncode != 0:
        git("reset")
        return fail("git commit failed")

    new_head = git("rev-parse", "HEAD").stdout.strip()

    # Race protection:
    # somebody could have pushed after our initial fetch.
    fetch2 = git("fetch", "origin", "main", check=False)
    if fetch2.returncode != 0:
        return fail(
            "second fetch failed; checkpoint committed locally but not pushed"
        )

    remote_after = git("rev-parse", "origin/main").stdout.strip()

    if remote_after != local_before:
        return fail(
            "origin/main changed during checkpoint; "
            "local checkpoint retained but push refused"
        )

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
    )

    print("GIT_CHECKPOINT_PUBLISHED", new_head)
    print("GIT_CHECKPOINT_FILE_COUNT", len(staged))

    for path in staged:
        print("GIT_CHECKPOINT_FILE", path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
