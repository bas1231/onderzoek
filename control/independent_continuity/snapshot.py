"""Pin and materialize immutable build-log events from a fetched Git commit.

No working-tree checkout, Git fetch, remote write, credentials or network.
Fails closed on malformed archive entries and size limits.
"""
from __future__ import annotations

import io
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile


class SnapshotError(ValueError):
    pass


SHA = re.compile(r"^[a-f0-9]{40}$")
PREFIX = "control/build_log/events/"
MAX_ARCHIVE = 48 * 1024 * 1024
MAX_EVENTS = 12000
MAX_ENTRY = 1024 * 1024


def snapshot_events(repo: Path, destination: Path) -> dict:
    if not (repo / ".git").is_dir():
        raise SnapshotError("snapshot mirror is not a git worktree")
    if destination.exists() and any(destination.iterdir()):
        raise SnapshotError("snapshot destination must be empty")
    destination.mkdir(parents=True, exist_ok=True)
    try:
        head = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--verify", "FETCH_HEAD"],
            capture_output=True, check=True, text=True, timeout=10
        ).stdout.strip()
        if not SHA.fullmatch(head):
            raise SnapshotError("missing pinned fetched revision")
        data = subprocess.run(
            ["git", "-C", str(repo), "archive", "--format=tar",
             head, "control/build_log/events"],
            capture_output=True, check=True, timeout=30
        ).stdout
        if len(data) > MAX_ARCHIVE:
            raise SnapshotError("snapshot size cap")
        count = 0
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
            for member in archive:
                if member.isdir():
                    continue
                if not member.isfile() or member.issym() or member.islnk():
                    raise SnapshotError("non-regular archive member forbidden")
                name = member.name
                tail = name[len(PREFIX):] if name.startswith(PREFIX) else ""
                if (not tail or "/" in tail or not tail.endswith(".json")
                        or PurePosixPath(tail).name != tail):
                    raise SnapshotError("unexpected archive entry")
                if member.size > MAX_ENTRY:
                    raise SnapshotError("oversized ledger event")
                count += 1
                if count > MAX_EVENTS:
                    raise SnapshotError("ledger event cap")
                stream = archive.extractfile(member)
                if stream is None:
                    raise SnapshotError("archive entry unreadable")
                raw = stream.read(MAX_ENTRY + 1)
                if len(raw) != member.size:
                    raise SnapshotError("snapshot event size mismatch")
                (destination / tail).write_bytes(raw)
        return {"source_commit": head, "event_files": count}
    except (OSError, subprocess.SubprocessError, tarfile.TarError) as exc:
        raise SnapshotError("cannot read pinned fetched Git snapshot") from exc
