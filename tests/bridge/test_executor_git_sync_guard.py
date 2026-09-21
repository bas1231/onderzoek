import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control"))

import executor


def test_executor_blocks_before_parsing_or_mutating_task(monkeypatch, tmp_path):
    task_file = tmp_path / "still-pending.json"
    task_file.write_text("{not valid json", encoding="utf-8")

    monkeypatch.setattr(
        executor,
        "inspect_remote_write_safety",
        lambda root: SimpleNamespace(
            safe_to_write=False,
            status="LOCAL_BEHIND",
            detail="origin/main is newer",
        ),
    )

    outcome = executor.process_task(task_file)

    assert outcome == "git_sync_blocked"
    assert task_file.exists()
    assert task_file.read_text(encoding="utf-8") == "{not valid json"


def test_executor_only_continues_after_exact_sync(monkeypatch, tmp_path):
    task_file = tmp_path / "malformed-after-sync.json"
    task_file.write_text("{not valid json", encoding="utf-8")

    monkeypatch.setattr(
        executor,
        "inspect_remote_write_safety",
        lambda root: SimpleNamespace(
            safe_to_write=True,
            status="SYNCED",
            detail="exact sync",
        ),
    )

    with pytest.raises(json.JSONDecodeError):
        executor.process_task(task_file)
