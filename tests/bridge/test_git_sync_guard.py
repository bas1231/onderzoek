from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control"))

from git_sync_guard import (
    inspect_remote_write_safety,
    require_remote_write_safety,
)


def git(cwd: Path, *args: str, check: bool = True):
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=check,
    )


def configure(repo: Path, name: str) -> None:
    git(repo, "config", "user.email", f"{name.lower()}@example.test")
    git(repo, "config", "user.name", name)


def commit_file(repo: Path, name: str, content: str, message: str) -> None:
    (repo / name).write_text(content, encoding="utf-8")
    git(repo, "add", "--", name)
    git(repo, "commit", "-qm", message)


def make_pair(tmp_path: Path) -> tuple[Path, Path, Path]:
    origin = tmp_path / "origin.git"
    local = tmp_path / "local"
    peer = tmp_path / "peer"

    git(tmp_path, "init", "--bare", "-q", str(origin))
    git(tmp_path, "clone", "-q", str(origin), str(local))
    configure(local, "Local")
    git(local, "checkout", "-qb", "main")
    commit_file(local, "baseline.txt", "one\n", "baseline")
    git(local, "push", "-qu", "origin", "main")

    git(tmp_path, "clone", "-q", str(origin), str(peer))
    configure(peer, "Peer")
    git(peer, "checkout", "-q", "main")

    return origin, local, peer


def test_synced_main_is_safe(tmp_path):
    _, local, _ = make_pair(tmp_path)

    state = inspect_remote_write_safety(root=local)

    assert state.safe_to_write is True
    assert state.status == "SYNCED"
    assert state.local_head == state.remote_head


def test_local_ahead_is_blocked(tmp_path):
    _, local, _ = make_pair(tmp_path)
    commit_file(local, "local.txt", "local\n", "local ahead")

    state = inspect_remote_write_safety(root=local)

    assert state.safe_to_write is False
    assert state.status == "LOCAL_AHEAD"
    assert state.local_head != state.remote_head


def test_local_behind_is_blocked(tmp_path):
    _, local, peer = make_pair(tmp_path)
    commit_file(peer, "remote.txt", "remote\n", "remote ahead")
    git(peer, "push", "-q", "origin", "main")

    state = inspect_remote_write_safety(root=local)

    assert state.safe_to_write is False
    assert state.status == "LOCAL_BEHIND"


def test_diverged_is_blocked(tmp_path):
    _, local, peer = make_pair(tmp_path)
    commit_file(peer, "remote.txt", "remote\n", "remote ahead")
    git(peer, "push", "-q", "origin", "main")
    commit_file(local, "local.txt", "local\n", "local diverges")

    state = inspect_remote_write_safety(root=local)

    assert state.safe_to_write is False
    assert state.status == "DIVERGED"


def test_wrong_branch_is_blocked_without_fetch(tmp_path):
    _, local, _ = make_pair(tmp_path)
    git(local, "checkout", "-qb", "feature")

    state = inspect_remote_write_safety(root=local, fetch=False)

    assert state.safe_to_write is False
    assert state.status == "WRONG_BRANCH"
    assert state.branch == "feature"


def test_require_guard_raises_on_behind(tmp_path):
    _, local, peer = make_pair(tmp_path)
    commit_file(peer, "remote.txt", "remote\n", "remote ahead")
    git(peer, "push", "-q", "origin", "main")

    with pytest.raises(RuntimeError, match="LOCAL_BEHIND"):
        require_remote_write_safety(root=local)


def test_require_guard_raises_on_local_ahead(tmp_path):
    _, local, _ = make_pair(tmp_path)
    commit_file(local, "local.txt", "local\n", "local ahead")

    with pytest.raises(RuntimeError, match="LOCAL_AHEAD"):
        require_remote_write_safety(root=local)
