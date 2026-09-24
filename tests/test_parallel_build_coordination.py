import importlib.util
import json
import subprocess
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "control" / "jobs" / "parallel_build_coordination.py"
spec = importlib.util.spec_from_file_location("parallel_build_coordination", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()


def make_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "Test")
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-m", "init")
    return root


def test_path_overlap_prefixes():
    assert module.paths_overlap("control/scheduler", "control/scheduler/x.py")
    assert module.paths_overlap("control/scheduler/**", "control/scheduler/x.py")
    assert not module.paths_overlap("control/scheduler", "control/nightshift")


def test_same_worktree_blocks_even_nonoverlapping_paths(tmp_path):
    root = make_repo(tmp_path)
    coord = module.Coordinator(root, ttl_seconds=300)
    assert coord.start("A", "TASK-A", ["control/scheduler"], mutating=True, ttl=300)["ok"]
    second = coord.start("B", "TASK-B", ["control/nightshift"], mutating=True, ttl=300)
    assert second["ok"] is False
    assert second["status"] == "BLOCKED_PARALLEL_CONFLICT"
    assert second["conflicts"][0]["same_worktree"] is True


def test_overlapping_paths_block_across_distinct_worktrees(tmp_path):
    root = make_repo(tmp_path)
    coord = module.Coordinator(root, ttl_seconds=300)
    assert coord.start("A", "TASK-A", ["control/scheduler"], mutating=True, ttl=300)["ok"]
    lease_path = coord._session_file("A")
    lease = json.loads(lease_path.read_text(encoding="utf-8"))
    lease["worktree"] = str(root / "other-worktree")
    lease_path.write_text(json.dumps(lease), encoding="utf-8")
    second = coord.start("B", "TASK-B", ["control/scheduler/timer.py"], mutating=True, ttl=300)
    assert second["ok"] is False
    assert second["conflicts"][0]["path_overlaps"]


def test_distinct_worktrees_nonoverlap_are_allowed(tmp_path):
    root = make_repo(tmp_path)
    coord = module.Coordinator(root, ttl_seconds=300)
    assert coord.start("A", "TASK-A", ["control/scheduler"], mutating=True, ttl=300)["ok"]
    lease_path = coord._session_file("A")
    lease = json.loads(lease_path.read_text(encoding="utf-8"))
    lease["worktree"] = str(root / "other-worktree")
    lease_path.write_text(json.dumps(lease), encoding="utf-8")
    second = coord.start("B", "TASK-B", ["control/nightshift"], mutating=True, ttl=300)
    assert second["ok"] is True


def test_expired_session_does_not_block(tmp_path):
    root = make_repo(tmp_path)
    coord = module.Coordinator(root, ttl_seconds=30)
    assert coord.start("A", "TASK-A", ["control/scheduler"], mutating=True, ttl=30)["ok"]
    lease_path = coord._session_file("A")
    lease = json.loads(lease_path.read_text(encoding="utf-8"))
    lease["expires_at_epoch"] = 1
    lease_path.write_text(json.dumps(lease), encoding="utf-8")
    assert coord.start("B", "TASK-B", ["control/nightshift"], mutating=True, ttl=30)["ok"]


def test_integration_lock_is_exclusive(tmp_path):
    root = make_repo(tmp_path)
    coord = module.Coordinator(root, ttl_seconds=300)
    assert coord.start("A", "TASK-A", ["control/scheduler"], mutating=True, ttl=300)["ok"]
    a_path = coord._session_file("A")
    a = json.loads(a_path.read_text(encoding="utf-8"))
    a["worktree"] = str(root / "worktree-A")
    a_path.write_text(json.dumps(a), encoding="utf-8")
    assert coord.start("B", "TASK-B", ["control/nightshift"], mutating=True, ttl=300)["ok"]
    assert coord.acquire_integration("A")["ok"]
    blocked = coord.acquire_integration("B")
    assert blocked["ok"] is False
    assert blocked["status"] == "BLOCKED_INTEGRATION_LOCK"
