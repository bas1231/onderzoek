from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control"))

from executor_preflight import task_provenance_in_head


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )


def init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "config", "user.name", "Preflight Test")
    (repo / "control/tasks/pending").mkdir(parents=True)
    (repo / "control/jobs").mkdir(parents=True)
    (repo / "tests/bridge").mkdir(parents=True)
    return repo


def write_task(repo: Path, task_id: str, script: str) -> Path:
    path = repo / "control/tasks/pending" / f"{task_id}.json"
    path.write_text(
        json.dumps(
            {
                "task_id": task_id,
                "hypothesis_id": "TEST-001",
                "task_class": "research",
                "operation": "python",
                "working_directory": ".",
                "command": ["python3", script],
                "timeout_seconds": 60,
                "live_trading": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def write_pytest_task(repo: Path, task_id: str, target: str) -> Path:
    path = repo / "control/tasks/pending" / f"{task_id}.json"
    path.write_text(
        json.dumps(
            {
                "task_id": task_id,
                "hypothesis_id": "TEST-001",
                "task_class": "research",
                "operation": "pytest",
                "working_directory": ".",
                "command": ["python3", "-m", "pytest", target, "-q"],
                "timeout_seconds": 60,
                "live_trading": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def commit_all(repo: Path, message: str) -> str:
    git(repo, "add", ".")
    git(repo, "commit", "-m", message)
    return git(repo, "rev-parse", "HEAD").stdout.strip()


def test_same_commit_task_and_script_pass(tmp_path: Path):
    repo = init_repo(tmp_path)
    script = repo / "control/jobs/job.py"
    script.write_text("print('ok')\n", encoding="utf-8")
    task = write_task(repo, "TASK-SAME", "control/jobs/job.py")
    commit_all(repo, "task and script atomically")

    out = task_provenance_in_head(repo, task)
    assert out["ok"] is True
    assert out["support_provenance"]["status"] == "SUPPORT_SCRIPT_BOUND_TO_TASK_COMMIT"


def test_later_added_script_does_not_rescue_old_task(tmp_path: Path):
    repo = init_repo(tmp_path)
    task = write_task(repo, "TASK-MISSING", "control/jobs/later.py")
    task_commit = commit_all(repo, "task before script")

    (repo / "control/jobs/later.py").write_text("print('late')\n", encoding="utf-8")
    commit_all(repo, "add script later")

    out = task_provenance_in_head(repo, task)
    assert out["ok"] is False
    assert out["reason"] == "SUPPORT_SCRIPT_NOT_IN_TASK_COMMIT"
    assert out["task_commit"] == task_commit


def test_script_change_after_task_commit_fails_closed(tmp_path: Path):
    repo = init_repo(tmp_path)
    script = repo / "control/jobs/job.py"
    script.write_text("print('v1')\n", encoding="utf-8")
    task = write_task(repo, "TASK-CHANGED", "control/jobs/job.py")
    commit_all(repo, "task bound to script v1")

    script.write_text("print('v2')\n", encoding="utf-8")
    commit_all(repo, "change script after task")

    out = task_provenance_in_head(repo, task)
    assert out["ok"] is False
    assert out["reason"] == "SUPPORT_SCRIPT_CHANGED_AFTER_TASK_COMMIT"
    assert out["task_script_blob"] != out["execution_script_blob"]


def test_unchanged_task_and_script_can_run_from_descendant_head(tmp_path: Path):
    repo = init_repo(tmp_path)
    script = repo / "control/jobs/job.py"
    script.write_text("print('stable')\n", encoding="utf-8")
    task = write_task(repo, "TASK-DESCENDANT", "control/jobs/job.py")
    task_commit = commit_all(repo, "task and stable script")

    (repo / "README.md").write_text("unrelated later commit\n", encoding="utf-8")
    head = commit_all(repo, "unrelated change")

    out = task_provenance_in_head(repo, task)
    assert out["ok"] is True
    assert out["task_commit"] == task_commit
    assert out["execution_commit"] == head
    assert out["relationship"] == "ancestor"
    assert out["support_provenance"]["script"] == "control/jobs/job.py"


def test_same_commit_pytest_target_passes(tmp_path: Path):
    repo = init_repo(tmp_path)
    target = repo / "tests/bridge/test_target.py"
    target.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    task = write_pytest_task(repo, "PYTEST-SAME", "tests/bridge/test_target.py")
    commit_all(repo, "pytest task and target atomically")

    out = task_provenance_in_head(repo, task)
    assert out["ok"] is True
    assert out["support_provenance"]["status"] == "SUPPORT_SCRIPT_BOUND_TO_TASK_COMMIT"
    assert out["support_provenance"]["script"] == "tests/bridge/test_target.py"


def test_later_added_pytest_target_does_not_rescue_old_task(tmp_path: Path):
    repo = init_repo(tmp_path)
    task = write_pytest_task(repo, "PYTEST-MISSING", "tests/bridge/test_later.py")
    task_commit = commit_all(repo, "pytest task before target")

    target = repo / "tests/bridge/test_later.py"
    target.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    commit_all(repo, "add pytest target later")

    out = task_provenance_in_head(repo, task)
    assert out["ok"] is False
    assert out["reason"] == "SUPPORT_SCRIPT_NOT_IN_TASK_COMMIT"
    assert out["task_commit"] == task_commit


def test_pytest_target_change_after_task_commit_fails_closed(tmp_path: Path):
    repo = init_repo(tmp_path)
    target = repo / "tests/bridge/test_target.py"
    target.write_text("def test_v1():\n    assert True\n", encoding="utf-8")
    task = write_pytest_task(repo, "PYTEST-CHANGED", "tests/bridge/test_target.py::test_v1")
    commit_all(repo, "pytest task bound to target v1")

    target.write_text("def test_v2():\n    assert True\n", encoding="utf-8")
    commit_all(repo, "change pytest target later")

    out = task_provenance_in_head(repo, task)
    assert out["ok"] is False
    assert out["reason"] == "SUPPORT_SCRIPT_CHANGED_AFTER_TASK_COMMIT"
    assert out["task_script_blob"] != out["execution_script_blob"]
