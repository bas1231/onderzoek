from pathlib import Path
import json
import tempfile

import pytest

ROOT = Path(__file__).resolve().parents[2]

import sys
sys.path.insert(0, str(ROOT / "control"))

from edge_hunter import prebuild_warrant
from edge_hunter.build_gate import authorize_task
from validator import Task


def control_auth(capabilities=None):
    return {
        "mode": "control_plane",
        "build_kind": "control_plane",
        "objective": "Harden the research control plane",
        "capabilities": capabilities or [],
    }


def infra_task(authorization=None, hypothesis_id="CONTROL-EHB-002"):
    return {
        "task_id": "INFRA-EHB-002-TEST",
        "hypothesis_id": hypothesis_id,
        "task_class": "infrastructure",
        "operation": "python",
        "working_directory": ".",
        "command": ["python", "control/jobs/ehb002_test.py"],
        "timeout_seconds": 120,
        "live_trading": False,
        "build_authorization": authorization,
    }


def research_task():
    return {
        "task_id": "RESEARCH-EHB-002-TEST",
        "hypothesis_id": "RESEARCH-EHB-002",
        "task_class": "research",
        "operation": "python",
        "working_directory": ".",
        "command": ["python", "control/jobs/ehb002_test.py"],
        "timeout_seconds": 120,
        "live_trading": False,
    }


def setup_candidate_root(path: Path):
    (path / "control/edge_hunter").mkdir(parents=True)
    (path / "knowledge/candidates").mkdir(parents=True)
    (path / "knowledge/warrants").mkdir(parents=True)

    policy = json.loads(
        (ROOT / "control/edge_hunter/warrant_policy.json").read_text()
    )
    state = json.loads(
        (ROOT / "control/BUILD_STATE.json").read_text()
    )

    (path / "control/edge_hunter/warrant_policy.json").write_text(
        json.dumps(policy)
    )
    (path / "control/BUILD_STATE.json").write_text(
        json.dumps(state)
    )
    (path / "control/AUTONOMOUS_BUILD_POLICY.json").write_text(
        (ROOT / "control/AUTONOMOUS_BUILD_POLICY.json").read_text()
    )

    candidate = {
        "candidate_id": "CAND-EHB-002",
        "lane": "market_algebra",
        "hypothesis": "A test candidate",
        "mechanism": "A defined test mechanism",
        "disconfirming_evidence": ["counterexample"],
        "point_in_time_requirements": ["archived inputs"],
        "signal_metric": "test metric",
        "market_edge_test": "test market edge",
        "execution_reality_test": "test execution reality",
        "phase": "PREBUILD_KILLED",
        "decision": "SURVIVES_STAGE",
        "gates": {
            "mechanism": "PASS",
            "prebuild_killer": "PASS",
        },
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
    }

    candidate_path = path / "knowledge/candidates/CAND-EHB-002.json"
    candidate_path.write_text(json.dumps(candidate))

    request = {
        "build_kind": "offline_analysis",
        "objective": "Build only offline candidate analysis",
        "capabilities": ["read_repository"],
    }

    warrant_path = prebuild_warrant.issue(
        candidate,
        request,
        warrant_dir=path / "knowledge/warrants",
        policy=policy,
        build_state=state,
    )

    authorization = {
        "mode": "candidate",
        **request,
        "warrant_ref": warrant_path.relative_to(path).as_posix(),
    }

    return candidate_path, authorization


def test_research_task_remains_unchanged():
    task = Task.model_validate(research_task())
    assert task.task_class == "research"


def test_infrastructure_without_authorization_fails_closed():
    with pytest.raises(Exception, match="missing_build_authorization"):
        Task.model_validate(infra_task())


def test_safe_control_plane_task_is_allowed():
    task = Task.model_validate(infra_task(control_auth()))
    assert task.build_authorization["mode"] == "control_plane"


def test_forbidden_control_plane_capability_is_denied():
    with pytest.raises(Exception, match="forbidden_capability:order_submission"):
        Task.model_validate(
            infra_task(control_auth(["order_submission"]))
        )


def test_research_task_cannot_smuggle_build_authorization():
    row = research_task()
    row["build_authorization"] = control_auth()

    with pytest.raises(
        Exception,
        match="build_authorization_on_non_infrastructure_task",
    ):
        Task.model_validate(row)


def test_valid_candidate_warrant_is_accepted():
    with tempfile.TemporaryDirectory() as td:
        temp_root = Path(td)
        _, authorization = setup_candidate_root(temp_root)
        row = infra_task(authorization, "CAND-EHB-002")

        result = authorize_task(row, root=temp_root)

        assert result["allowed"] is True
        assert result["decision"] == "ALLOW_CANDIDATE_BUILD"


def test_changed_request_invalidates_candidate_warrant():
    with tempfile.TemporaryDirectory() as td:
        temp_root = Path(td)
        _, authorization = setup_candidate_root(temp_root)
        authorization["objective"] = "A different objective"
        row = infra_task(authorization, "CAND-EHB-002")

        result = authorize_task(row, root=temp_root)

        assert result["allowed"] is False
        assert any(
            reason.startswith("stale_or_tampered_warrant:")
            for reason in result["reasons"]
        )


def test_changed_candidate_invalidates_candidate_warrant():
    with tempfile.TemporaryDirectory() as td:
        temp_root = Path(td)
        candidate_path, authorization = setup_candidate_root(temp_root)
        candidate = json.loads(candidate_path.read_text())
        candidate["hypothesis"] = "Changed after warrant issuance"
        candidate_path.write_text(json.dumps(candidate))
        row = infra_task(authorization, "CAND-EHB-002")

        result = authorize_task(row, root=temp_root)

        assert result["allowed"] is False
        assert "stale_or_tampered_warrant:candidate_sha256" in result["reasons"]


def test_build_freeze_invalidates_control_plane_authorization():
    with tempfile.TemporaryDirectory() as td:
        temp_root = Path(td)
        setup_candidate_root(temp_root)
        state_path = temp_root / "control/BUILD_STATE.json"
        state = json.loads(state_path.read_text())
        state["builds_enabled"] = False
        state_path.write_text(json.dumps(state))

        result = authorize_task(
            infra_task(control_auth()),
            root=temp_root,
        )

        assert result["allowed"] is False
        assert "build_freeze_active" in result["reasons"]
