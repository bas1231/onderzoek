from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control"))

from validator import Task


def head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()


def base_row(capabilities, include_contract):
    objective = "Build one bounded governed component"
    auth = {
        "mode": "control_plane",
        "build_kind": "control_plane",
        "objective": objective,
        "capabilities": capabilities,
    }
    if include_contract:
        auth["build_contract"] = {
            "build_id": "BUILD-BRIDGE-GOV-001",
            "protocol_version": 1,
            "objective": objective,
            "source_commit": head(),
            "allowed_capabilities": list(capabilities),
            "allowed_paths": ["control/example"],
            "planned_paths": ["control/example"],
            "acceptance_criteria": ["Validator accepts the frozen contract"],
            "non_goals": ["No unrelated changes"],
            "independent_verification": "Bridge regression suite",
            "rollback_plan": "Revert the build commit",
            "cleanup_plan": "No temporary resources",
            "max_attempts": 2,
            "governance_change": False,
            "safety": {
                "live_trading": False,
                "paid_actions": False,
                "wallet_actions": False,
            },
        }
    return {
        "task_id": "CONTROL-GOV-BRIDGE-TEST",
        "hypothesis_id": "CONTROL-AUTONOMOUS-GOVERNANCE",
        "task_class": "infrastructure",
        "operation": "python",
        "working_directory": ".",
        "command": [".venv/bin/python", "control/jobs/ehb002_test.py"],
        "timeout_seconds": 60,
        "live_trading": False,
        "build_authorization": auth,
    }


def test_read_only_infrastructure_remains_compatible():
    row = base_row(["read_repository"], include_contract=False)
    parsed = Task.model_validate(row)
    assert parsed.task_class == "infrastructure"


def test_mutating_infrastructure_without_contract_is_denied():
    row = base_row(["read_repository", "write_repository"], include_contract=False)
    with pytest.raises(Exception, match="missing_build_contract"):
        Task.model_validate(row)


def test_valid_mutating_infrastructure_contract_is_accepted():
    row = base_row(["read_repository", "write_repository"], include_contract=True)
    parsed = Task.model_validate(row)
    assert parsed.build_authorization["build_contract"]["build_id"] == "BUILD-BRIDGE-GOV-001"


def test_stale_source_commit_is_denied():
    row = base_row(["read_repository", "write_repository"], include_contract=True)
    row["build_authorization"]["build_contract"]["source_commit"] = "0" * 40
    with pytest.raises(Exception, match="build_contract_source_commit_mismatch"):
        Task.model_validate(row)
