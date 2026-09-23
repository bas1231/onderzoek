from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control"))

from edge_hunter.autonomous_build_governance import (
    validate_changed_paths,
    validate_task,
)


def head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()


def base_contract():
    objective = "Build one bounded autonomous-control component"
    return {
        "build_id": "BUILD-GOV-TEST-001",
        "protocol_version": 1,
        "objective": objective,
        "source_commit": head(),
        "allowed_capabilities": ["read_repository", "write_repository"],
        "allowed_paths": ["control/example", "tests/example"],
        "planned_paths": ["control/example", "tests/example"],
        "acceptance_criteria": ["Target test passes", "Regression remains green"],
        "non_goals": ["No unrelated refactor"],
        "independent_verification": "Separate regression test",
        "rollback_plan": "Revert the build commit",
        "cleanup_plan": "Remove temporary build-only artifacts",
        "max_attempts": 2,
        "governance_change": False,
        "safety": {
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
        },
    }


def task(capabilities=None, contract=True):
    capabilities = capabilities or ["read_repository", "write_repository"]
    objective = "Build one bounded autonomous-control component"
    authorization = {
        "mode": "control_plane",
        "build_kind": "control_plane",
        "objective": objective,
        "capabilities": capabilities,
    }
    if contract:
        authorization["build_contract"] = base_contract()
    return {
        "task_id": "GOV-TEST-001",
        "hypothesis_id": "CONTROL-GOVERNANCE",
        "task_class": "infrastructure",
        "build_authorization": authorization,
    }


def test_read_only_infrastructure_remains_backward_compatible():
    row = task(capabilities=["read_repository"], contract=False)
    result = validate_task(row)
    assert result["allowed"] is True
    assert result["decision"] == "ALLOW_READ_ONLY"


def test_mutating_infrastructure_requires_contract():
    row = task(contract=False)
    result = validate_task(row)
    assert result["allowed"] is False
    assert "missing_build_contract" in result["reasons"]


def test_valid_mutating_contract_is_allowed():
    result = validate_task(task())
    assert result == {
        "allowed": True,
        "decision": "ALLOW_GOVERNED_BUILD",
        "reasons": [],
    }


def test_source_commit_must_be_a_full_sha():
    row = task()
    row["build_authorization"]["build_contract"]["source_commit"] = "not-a-sha"
    result = validate_task(row)
    assert result["allowed"] is False
    assert "invalid_build_contract_source_commit" in result["reasons"]


def test_builder_cannot_change_objective_inside_contract():
    row = task()
    row["build_authorization"]["build_contract"]["objective"] = "Different objective"
    result = validate_task(row)
    assert result["allowed"] is False
    assert "build_contract_objective_mismatch" in result["reasons"]


def test_capabilities_cannot_escape_contract():
    row = task(capabilities=["read_repository", "write_repository", "restart_service"])
    result = validate_task(row)
    assert result["allowed"] is False
    assert "capability_outside_build_contract:restart_service" in result["reasons"]


def test_planned_paths_must_stay_inside_allowed_paths():
    row = task()
    row["build_authorization"]["build_contract"]["planned_paths"].append("outside/scope.py")
    result = validate_task(row)
    assert result["allowed"] is False
    assert "planned_path_outside_allowed_paths:outside/scope.py" in result["reasons"]


def test_safety_flags_fail_closed():
    row = task()
    row["build_authorization"]["build_contract"]["safety"]["paid_actions"] = True
    result = validate_task(row)
    assert result["allowed"] is False
    assert "unsafe_build_contract_flag:paid_actions" in result["reasons"]


def test_protected_path_needs_explicit_governance_authority():
    row = task()
    contract = row["build_authorization"]["build_contract"]
    contract["allowed_paths"].append("AGENTS.md")
    contract["planned_paths"].append("AGENTS.md")
    result = validate_task(row)
    assert result["allowed"] is False
    assert "protected_path_requires_governance_change" in result["reasons"]
    assert "protected_path_requires_governance_capability" in result["reasons"]


def test_explicit_governance_change_can_touch_protected_path():
    row = task(capabilities=["read_repository", "write_repository", "governance_change"])
    contract = row["build_authorization"]["build_contract"]
    contract["allowed_capabilities"].append("governance_change")
    contract["allowed_paths"].append("AGENTS.md")
    contract["planned_paths"].append("AGENTS.md")
    contract["governance_change"] = True
    result = validate_task(row)
    assert result["allowed"] is True


def test_post_build_diff_cannot_escape_frozen_plan():
    row = task()
    ok = validate_changed_paths(row, ["control/example/file.py"])
    bad = validate_changed_paths(row, ["control/example/file.py", "README.md"])
    assert ok["allowed"] is True
    assert bad["allowed"] is False
    assert "changed_path_outside_plan:README.md" in bad["reasons"]
