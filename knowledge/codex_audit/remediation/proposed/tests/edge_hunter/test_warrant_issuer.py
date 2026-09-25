from pathlib import Path
import json
import subprocess
import sys
import tempfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control"))

from edge_hunter.build_gate import authorize_task
from jobs.issue_prebuild_warrant import issue_request, safe_request_path


def setup_root(path: Path, *, phase: str = "PREBUILD_KILLED") -> Path:
    (path / "control/edge_hunter").mkdir(parents=True)
    (path / "knowledge/candidates").mkdir(parents=True)
    (path / "knowledge/warrants").mkdir(parents=True)
    (path / "experiments/bridge/warrant_requests").mkdir(parents=True)

    policy = json.loads(
        (ROOT / "control/edge_hunter/warrant_policy.json").read_text()
    )
    build_state = json.loads(
        (ROOT / "control/BUILD_STATE.json").read_text()
    )

    (path / "control/edge_hunter/warrant_policy.json").write_text(
        json.dumps(policy)
    )
    (path / "control/BUILD_STATE.json").write_text(
        json.dumps(build_state)
    )

    (path / "control/AUTONOMOUS_BUILD_POLICY.json").write_text(
        (ROOT / "control/AUTONOMOUS_BUILD_POLICY.json").read_text()
    )

    candidate = {
        "candidate_id": "CAND-EHB-003",
        "lane": "market_algebra",
        "hypothesis": "Test candidate",
        "mechanism": "Defined mechanism",
        "disconfirming_evidence": ["counterexample"],
        "point_in_time_requirements": ["archived inputs"],
        "signal_metric": "metric",
        "market_edge_test": "market test",
        "execution_reality_test": "execution test",
        "phase": phase,
        "decision": "SURVIVES_STAGE",
        "gates": {
            "mechanism": "PASS",
            "prebuild_killer": "PASS",
        },
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
    }
    (path / "knowledge/candidates/CAND-EHB-003.json").write_text(
        json.dumps(candidate)
    )

    request = {
        "candidate_id": "CAND-EHB-003",
        "build_kind": "offline_analysis",
        "objective": "Bounded offline candidate analysis",
        "capabilities": ["read_repository"],
    }
    request_path = (
        path / "experiments/bridge/warrant_requests/request.json"
    )
    request_path.write_text(json.dumps(request))

    return request_path


def init_git(path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=path,
        check=True,
    )
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "baseline"],
        cwd=path,
        check=True,
    )


def test_safe_request_path_rejects_traversal():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        setup_root(root)

        with pytest.raises(ValueError):
            safe_request_path("../request.json", root=root)


def test_unknown_request_field_is_rejected():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        request_path = setup_root(root)
        payload = json.loads(request_path.read_text())
        payload["unexpected"] = True
        request_path.write_text(json.dumps(payload))

        with pytest.raises(ValueError, match="unknown warrant request fields"):
            issue_request(request_path, root=root, stage=False)


def test_missing_request_field_is_rejected():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        request_path = setup_root(root)
        payload = json.loads(request_path.read_text())
        payload.pop("objective")
        request_path.write_text(json.dumps(payload))

        with pytest.raises(ValueError, match="missing warrant request fields"):
            issue_request(request_path, root=root, stage=False)


def test_valid_request_issues_warrant():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        request_path = setup_root(root)

        result = issue_request(request_path, root=root, stage=False)

        assert result["issued"] is True
        assert result["warrant_ref"].startswith("knowledge/warrants/")
        assert (root / result["warrant_ref"]).exists()


def test_prebuild_phase_denies_without_warrant():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        request_path = setup_root(root, phase="MECHANISM_DEFINED")

        result = issue_request(request_path, root=root, stage=False)

        assert result["issued"] is False
        assert "phase_below_minimum:PREBUILD_KILLED" in result["reasons"]
        assert list((root / "knowledge/warrants").glob("*.json")) == []


def test_forbidden_capability_denies_without_warrant():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        request_path = setup_root(root)
        payload = json.loads(request_path.read_text())
        payload["capabilities"] = ["order_submission"]
        request_path.write_text(json.dumps(payload))

        result = issue_request(request_path, root=root, stage=False)

        assert result["issued"] is False
        assert "forbidden_capability:order_submission" in result["reasons"]
        assert list((root / "knowledge/warrants").glob("*.json")) == []


def test_issued_warrant_is_accepted_by_build_gate():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        request_path = setup_root(root)
        result = issue_request(request_path, root=root, stage=False)

        task = {
            "task_id": "CANDIDATE-BUILD-EHB-003",
            "hypothesis_id": "CAND-EHB-003",
            "task_class": "infrastructure",
            "build_authorization": {
                "mode": "candidate",
                "build_kind": "offline_analysis",
                "objective": "Bounded offline candidate analysis",
                "capabilities": ["read_repository"],
                "warrant_ref": result["warrant_ref"],
            },
        }

        decision = authorize_task(task, root=root)

        assert decision["allowed"] is True
        assert decision["decision"] == "ALLOW_CANDIDATE_BUILD"


def test_warrant_is_staged_for_executor_commit():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        request_path = setup_root(root)
        init_git(root)

        result = issue_request(request_path, root=root, stage=True)

        staged = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=root,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.splitlines()

        assert result["staged_for_executor_commit"] is True
        assert result["warrant_ref"] in staged
        assert all(
            name.startswith("knowledge/warrants/")
            for name in staged
        )
