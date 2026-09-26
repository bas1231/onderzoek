from pathlib import Path
import sys

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "control"))

from executor_preflight import _runtime_dirty_allowed


def test_expected_runtime_paths_are_allowed():
    assert _runtime_dirty_allowed("knowledge/codex_runtime/STATE.json")
    assert _runtime_dirty_allowed("knowledge/codex_runtime/TASK_QUEUE.jsonl")
    assert _runtime_dirty_allowed("knowledge/candidates/X.json")
    assert _runtime_dirty_allowed("knowledge/research_os/evidence_graph.json")
    assert _runtime_dirty_allowed("knowledge/recon/watchlist.json")
    assert _runtime_dirty_allowed("hourly-reports/hourly-test.md")


def test_code_and_policy_paths_remain_blocked():
    assert not _runtime_dirty_allowed("control/executor.py")
    assert not _runtime_dirty_allowed("control/executor_preflight.py")
    assert not _runtime_dirty_allowed("control/codex_supervisor/supervisor.py")
    assert not _runtime_dirty_allowed("tests/codex_supervisor/test_supervisor.py")
    assert not _runtime_dirty_allowed("experiments/foo.py")
