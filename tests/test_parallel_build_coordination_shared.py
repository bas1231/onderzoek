import importlib.util
import subprocess
import sys
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "control" / "jobs" / "parallel_build_coordination_shared.py"
MODULE_DIR = MODULE_PATH.parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))
spec = importlib.util.spec_from_file_location("parallel_build_coordination_shared", MODULE_PATH)
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


def make_repo_with_worktrees(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "Test")
    (root / "seed.txt").write_text("seed\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-m", "init")

    wt_a = tmp_path / "worktree-a"
    wt_b = tmp_path / "worktree-b"
    wt_c = tmp_path / "worktree-c"
    git(root, "worktree", "add", "-b", "session-a", str(wt_a), "HEAD")
    git(root, "worktree", "add", "-b", "session-b", str(wt_b), "HEAD")
    git(root, "worktree", "add", "-b", "session-c", str(wt_c), "HEAD")
    return root, wt_a, wt_b, wt_c


def test_real_worktrees_share_one_registry_and_detect_conflicts(tmp_path):
    root, wt_a, wt_b, wt_c = make_repo_with_worktrees(tmp_path)
    coord_a = module.Coordinator(wt_a, ttl_seconds=300)
    coord_b = module.Coordinator(wt_b, ttl_seconds=300)
    coord_c = module.Coordinator(wt_c, ttl_seconds=300)

    assert coord_a.runtime == coord_b.runtime == coord_c.runtime
    assert coord_a.runtime.parent == (root / ".git").resolve()

    first = coord_a.start("A", "TASK-A", ["control/scheduler/**"], mutating=True, ttl=300)
    assert first["ok"] is True

    nonoverlap = coord_b.start("B", "TASK-B", ["control/nightshift/**"], mutating=True, ttl=300)
    assert nonoverlap["ok"] is True

    overlap = coord_c.start("C", "TASK-C", ["control/scheduler/timer.py"], mutating=True, ttl=300)
    assert overlap["ok"] is False
    assert overlap["status"] == "BLOCKED_PARALLEL_CONFLICT"
    assert overlap["conflicts"][0]["session_id"] == "A"
    assert overlap["conflicts"][0]["path_overlaps"]


def test_real_worktrees_share_exclusive_integration_lock(tmp_path):
    _, wt_a, wt_b, _ = make_repo_with_worktrees(tmp_path)
    coord_a = module.Coordinator(wt_a, ttl_seconds=300)
    coord_b = module.Coordinator(wt_b, ttl_seconds=300)

    assert coord_a.start("A", "TASK-A", ["control/scheduler/**"], mutating=True, ttl=300)["ok"]
    assert coord_b.start("B", "TASK-B", ["control/nightshift/**"], mutating=True, ttl=300)["ok"]

    assert coord_a.acquire_integration("A")["ok"] is True
    blocked = coord_b.acquire_integration("B")
    assert blocked["ok"] is False
    assert blocked["status"] == "BLOCKED_INTEGRATION_LOCK"
