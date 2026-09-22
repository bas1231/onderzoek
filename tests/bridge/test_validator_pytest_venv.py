from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
CONTROL = ROOT / "control"
if str(CONTROL) not in sys.path:
    sys.path.insert(0, str(CONTROL))

from validator import Task  # noqa: E402


def base_task(command: list[str]) -> dict:
    return {
        "task_id": "TEST-PYTEST-VENV-001",
        "hypothesis_id": "CONTROL-PYTEST-VENV",
        "task_class": "research",
        "operation": "pytest",
        "working_directory": ".",
        "command": command,
        "timeout_seconds": 60,
        "live_trading": False,
    }


def test_pytest_accepts_project_virtualenv_python():
    task = Task.model_validate(
        base_task([
            ".venv/bin/python",
            "-m",
            "pytest",
            "tests/bridge/test_bridge_runtime_attestation.py",
            "-q",
        ])
    )
    assert task.command[0] == ".venv/bin/python"


@pytest.mark.parametrize("executable", ["python3", "python"])
def test_pytest_rejects_non_project_python(executable: str):
    with pytest.raises(ValidationError, match="pytest must use project virtualenv python"):
        Task.model_validate(
            base_task([
                executable,
                "-m",
                "pytest",
                "tests/bridge/test_bridge_runtime_attestation.py",
                "-q",
            ])
        )


def test_pytest_still_rejects_non_module_invocation():
    with pytest.raises(ValidationError, match="pytest must run through python -m pytest"):
        Task.model_validate(
            base_task([
                ".venv/bin/python",
                "tests/bridge/test_bridge_runtime_attestation.py",
                "-q",
            ])
        )
