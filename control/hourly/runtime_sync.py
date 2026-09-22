from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
import json
import os
import subprocess


ROOT = Path(
    os.environ.get(
        "PREDICTION_RESEARCH_ROOT",
        Path(__file__).resolve().parents[2],
    )
).resolve()
STATUS_PATH = Path(
    os.environ.get(
        "PREDICTION_RUNTIME_SYNC_STATUS",
        Path.home() / ".local/state/prediction-research/runtime-sync-latest.json",
    )
)
REMOTE = os.environ.get("PREDICTION_RUNTIME_SYNC_REMOTE", "origin")
BRANCH = os.environ.get("PREDICTION_RUNTIME_SYNC_BRANCH", "main")

# Runtime/cache state that may remain dirty across an unrelated code fast-forward.
# An update is still refused when the incoming commit touches the same file.
EPHEMERAL_PREFIXES = (
    "knowledge/raw/",
    "knowledge/documents/",
    "knowledge/runs/source_sweeps/",
    "knowledge/runs/agent_packets/",
    "knowledge/runs/edge_hunter/",
    "knowledge/runs/recon/",
    "knowledge/runs/recon_hunts/",
    "knowledge/ai_exchange/",
)
EPHEMERAL_EXACT = {
    "knowledge/recon/watchlist.json",
    "knowledge/recon/opportunity_graph.json",
}

# These services can execute the hourly checkpoint publisher. Skip rather than
# race a commit/push against the fast-forward updater.
WRITER_SERVICES = (
    "prediction-research-hourly-director.service",
    "prediction-runtime-cycle-smoke.service",
)


class RuntimeSyncError(RuntimeError):
    pass


@dataclass(frozen=True)
class DirtyEntry:
    status: str
    path: str


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git(
    root: Path,
    *args: str,
    check: bool = True,
    timeout: int = 45,
) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
    )
    if check and proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()[-2000:]
        raise RuntimeSyncError(f"git {' '.join(args)} failed: {detail}")
    return proc


def parse_status(text: str) -> list[DirtyEntry]:
    out: list[DirtyEntry] = []
    for line in text.splitlines():
        if len(line) < 4:
            continue
        status = line[:2]
        raw_path = line[3:]
        if " -> " in raw_path:
            source, destination = raw_path.split(" -> ", 1)
            out.append(DirtyEntry(status=status, path=source))
            out.append(DirtyEntry(status=status, path=destination))
        else:
            out.append(DirtyEntry(status=status, path=raw_path))
    return out


def is_ephemeral(path: str) -> bool:
    normalized = path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized in EPHEMERAL_EXACT or any(
        normalized.startswith(prefix) for prefix in EPHEMERAL_PREFIXES
    )


def classify_dirty(entries: Iterable[DirtyEntry]) -> tuple[list[str], list[str]]:
    allowed: set[str] = set()
    blocked: set[str] = set()
    for entry in entries:
        if is_ephemeral(entry.path):
            allowed.add(entry.path)
        else:
            blocked.add(entry.path)
    return sorted(allowed), sorted(blocked)


def _writer_services_active() -> list[str]:
    active: list[str] = []
    for service in WRITER_SERVICES:
        try:
            proc = subprocess.run(
                ["systemctl", "--user", "is-active", "--quiet", service],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=5,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
        if proc.returncode == 0:
            active.append(service)
    return active


def write_status(
    status_path: Path,
    status: str,
    *,
    remote: str,
    branch: str,
    **extra: object,
) -> None:
    status_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "PVA_RUNTIME_SYNC_STATUS_V1",
        "timestamp_utc": now_iso(),
        "status": status,
        "branch": branch,
        "remote": remote,
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        **extra,
    }
    tmp = status_path.with_suffix(status_path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tmp.replace(status_path)


def _result(status: str, **extra: object) -> dict[str, object]:
    return {
        "ok": status != "FAIL_CLOSED",
        "status": status,
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        **extra,
    }


def _fail(
    status_path: Path,
    reason: str,
    *,
    remote: str,
    branch: str,
    **extra: object,
) -> dict[str, object]:
    write_status(
        status_path,
        "FAIL_CLOSED",
        remote=remote,
        branch=branch,
        reason=reason,
        **extra,
    )
    return _result("FAIL_CLOSED", reason=reason, **extra)


def sync_once(
    root: Path = ROOT,
    *,
    status_path: Path = STATUS_PATH,
    remote: str = REMOTE,
    branch: str = BRANCH,
    check_writer_services: bool = True,
) -> dict[str, object]:
    root = root.resolve()

    if not (root / ".git").exists():
        return _fail(
            status_path,
            "runtime root is not a normal git checkout",
            remote=remote,
            branch=branch,
            root=str(root),
        )

    if check_writer_services:
        active_writers = _writer_services_active()
        if active_writers:
            write_status(
                status_path,
                "SKIPPED_WRITER_ACTIVE",
                remote=remote,
                branch=branch,
                root=str(root),
                active_writers=active_writers,
            )
            return _result(
                "SKIPPED_WRITER_ACTIVE",
                root=str(root),
                active_writers=active_writers,
            )

    current_branch = _git(root, "branch", "--show-current").stdout.strip()
    if current_branch != branch:
        return _fail(
            status_path,
            f"unexpected branch: {current_branch!r}",
            remote=remote,
            branch=branch,
            root=str(root),
            expected_branch=branch,
        )

    # Runtime writers never need the git index. Anything staged is therefore a
    # human/build action and must block an automatic update, even on an
    # otherwise allowed runtime-state path.
    staged = sorted(
        value
        for value in _git(root, "diff", "--cached", "--name-only").stdout.splitlines()
        if value
    )
    if staged:
        return _fail(
            status_path,
            "git index is non-empty",
            remote=remote,
            branch=branch,
            root=str(root),
            staged_paths=staged,
        )

    status_text = _git(
        root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    ).stdout
    entries = parse_status(status_text)
    allowed_dirty, blocked_dirty = classify_dirty(entries)
    if blocked_dirty:
        return _fail(
            status_path,
            "unexpected dirty paths block runtime update",
            remote=remote,
            branch=branch,
            root=str(root),
            allowed_dirty=allowed_dirty,
            blocked_dirty=blocked_dirty,
        )

    fetch = _git(root, "fetch", remote, branch, check=False)
    if fetch.returncode != 0:
        detail = (fetch.stderr or fetch.stdout or "").strip()[-2000:]
        return _fail(
            status_path,
            f"git fetch {remote} {branch} failed",
            remote=remote,
            branch=branch,
            root=str(root),
            detail=detail,
            allowed_dirty=allowed_dirty,
        )

    remote_ref = f"{remote}/{branch}"
    local_head = _git(root, "rev-parse", "HEAD").stdout.strip()
    remote_head = _git(root, "rev-parse", remote_ref).stdout.strip()

    if local_head == remote_head:
        write_status(
            status_path,
            "UP_TO_DATE",
            remote=remote,
            branch=branch,
            root=str(root),
            head=local_head,
            allowed_dirty=allowed_dirty,
        )
        return _result(
            "UP_TO_DATE",
            head=local_head,
            allowed_dirty=allowed_dirty,
        )

    ancestor = _git(
        root,
        "merge-base",
        "--is-ancestor",
        local_head,
        remote_head,
        check=False,
    )
    if ancestor.returncode != 0:
        return _fail(
            status_path,
            "local HEAD is ahead of or diverged from fetched main",
            remote=remote,
            branch=branch,
            root=str(root),
            local_head=local_head,
            remote_head=remote_head,
            allowed_dirty=allowed_dirty,
        )

    incoming = sorted(
        {
            value
            for value in _git(
                root,
                "diff",
                "--name-only",
                f"{local_head}..{remote_head}",
            ).stdout.splitlines()
            if value
        }
    )
    overlap = sorted(set(allowed_dirty).intersection(incoming))
    if overlap:
        return _fail(
            status_path,
            "incoming update overlaps preserved runtime state",
            remote=remote,
            branch=branch,
            root=str(root),
            local_head=local_head,
            remote_head=remote_head,
            incoming_paths=incoming,
            overlap_paths=overlap,
            allowed_dirty=allowed_dirty,
        )

    merge = _git(root, "merge", "--ff-only", remote_ref, check=False)
    if merge.returncode != 0:
        detail = (merge.stderr or merge.stdout or "").strip()[-2000:]
        return _fail(
            status_path,
            "fast-forward update failed",
            remote=remote,
            branch=branch,
            root=str(root),
            local_head=local_head,
            remote_head=remote_head,
            incoming_paths=incoming,
            allowed_dirty=allowed_dirty,
            detail=detail,
        )

    final_head = _git(root, "rev-parse", "HEAD").stdout.strip()
    if final_head != remote_head:
        return _fail(
            status_path,
            "post-update HEAD mismatch",
            remote=remote,
            branch=branch,
            root=str(root),
            expected_head=remote_head,
            actual_head=final_head,
            allowed_dirty=allowed_dirty,
        )

    write_status(
        status_path,
        "UPDATED",
        remote=remote,
        branch=branch,
        root=str(root),
        previous_head=local_head,
        head=final_head,
        incoming_paths=incoming,
        allowed_dirty=allowed_dirty,
    )
    return _result(
        "UPDATED",
        previous_head=local_head,
        head=final_head,
        incoming_paths=incoming,
        allowed_dirty=allowed_dirty,
    )


def main() -> int:
    result = sync_once()
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
