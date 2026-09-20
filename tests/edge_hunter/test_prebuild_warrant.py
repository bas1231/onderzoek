from pathlib import Path
import importlib.util
import json
import tempfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "prebuild_warrant_testmod",
    ROOT / "control/edge_hunter/prebuild_warrant.py",
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

POLICY = json.loads((ROOT / "control/edge_hunter/warrant_policy.json").read_text())
BUILD_STATE = json.loads((ROOT / "control/BUILD_STATE.json").read_text())


def candidate():
    return {
        "candidate_id": "TEST-CANDIDATE-001",
        "lane": "market_algebra",
        "hypothesis": "h",
        "mechanism": "m",
        "disconfirming_evidence": ["d"],
        "point_in_time_requirements": ["p"],
        "signal_metric": "metric",
        "market_edge_test": "market",
        "execution_reality_test": "exec",
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


def request(**overrides):
    row = {
        "build_kind": "offline_analysis",
        "objective": "test the mechanism without execution",
        "capabilities": ["read_repository", "write_research_artifact"],
    }
    row.update(overrides)
    return row


def evaluate(row=None, req=None, state=None):
    return mod.evaluate(
        row if row is not None else candidate(),
        req if req is not None else request(),
        policy=POLICY,
        build_state=state if state is not None else BUILD_STATE,
    )


def test_allows_only_after_required_prebuild_gates():
    result = evaluate()
    assert result["decision"] == "ALLOW_RESEARCH_BUILD"
    assert result["reasons"] == []
    assert len(result["policy_sha256"]) == 64
    assert len(result["build_state_sha256"]) == 64


def test_denies_before_minimum_phase():
    row = candidate()
    row["phase"] = "MECHANISM_DEFINED"
    result = evaluate(row=row)
    assert result["decision"] == "DENY"
    assert "phase_below_minimum:PREBUILD_KILLED" in result["reasons"]


def test_denies_missing_prebuild_gate():
    row = candidate()
    row["gates"]["prebuild_killer"] = "PENDING"
    result = evaluate(row=row)
    assert "gate_not_pass:prebuild_killer" in result["reasons"]


def test_denies_forbidden_execution_capability():
    result = evaluate(req=request(capabilities=["read_repository", "order_submission"]))
    assert result["decision"] == "DENY"
    assert "forbidden_capability:order_submission" in result["reasons"]


def test_denies_unsafe_candidate_flag():
    row = candidate()
    row["paid_actions"] = True
    result = evaluate(row=row)
    assert result["decision"] == "DENY"
    assert "unsafe_candidate_flag:paid_actions" in result["reasons"]


def test_denies_when_build_freeze_is_active():
    state = dict(BUILD_STATE)
    state["builds_enabled"] = False
    result = evaluate(state=state)
    assert result["decision"] == "DENY"
    assert "build_freeze_active" in result["reasons"]


def test_malformed_capability_fails_closed_without_exception():
    result = evaluate(req=request(capabilities=["read_repository", {"bad": True}]))
    assert result["decision"] == "DENY"
    assert "invalid_capability" in result["reasons"]


def test_non_json_candidate_fails_closed_without_exception():
    row = candidate()
    row["bad"] = {1, 2}
    result = evaluate(row=row)
    assert result["decision"] == "DENY"
    assert "candidate_not_json_serializable" in result["reasons"]


def test_duplicate_capability_denied():
    result = evaluate(req=request(capabilities=["read_repository", "read_repository"]))
    assert result["decision"] == "DENY"
    assert "duplicate_capability" in result["reasons"]


def test_issue_persists_hashed_decision():
    with tempfile.TemporaryDirectory() as td:
        path = mod.issue(
            candidate(),
            request(),
            warrant_dir=Path(td),
            policy=POLICY,
            build_state=BUILD_STATE,
        )
        saved = json.loads(path.read_text())
        assert saved["decision"] == "ALLOW_RESEARCH_BUILD"
        assert len(saved["candidate_sha256"]) == 64
        assert len(saved["request_sha256"]) == 64
        assert len(saved["policy_sha256"]) == 64
        assert len(saved["build_state_sha256"]) == 64
        assert len(saved["decision_sha256"]) == 64
        assert saved["decision_sha256"][:12] in path.name
