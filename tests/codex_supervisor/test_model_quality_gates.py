from pathlib import Path
import json
import sys
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control/codex_supervisor"))

import model_quality_gate as q
import astra_review_wake as a
import measurement_wake as mw


class Supervisor:
    def __init__(self, root):
        self.root = root


def overlay(state="ASTRA_PREBUILD_REVIEW"):
    return {
        "candidate_id": "TINY-EDGE-CANARY",
        "queue_status": state,
        "source_hashes": {
            "knowledge/candidates/TINY-EDGE-CANARY.json": "a" * 64,
        },
        "originating_task_id": "CANDIDATE-TINY-EDGE-v1",
        "completion_hash": "b" * 64,
        "validation_hash": "c" * 64 if state == "ASTRA_PREMEASUREMENT_REVIEW" else None,
        "finding": "A tiny but potentially positive net executable edge is worth testing.",
        "next_action": "Build or measure only after independent Astra review.",
        "candidate_snapshot": {
            "candidate_id": "TINY-EDGE-CANARY",
            "prospective_protocols": [],
        },
        "referenced_evidence": {
            "knowledge/evidence/x.json": "{\"net_candidate_eur\":0.01}",
        },
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "remote_push": False,
    }


def write_review(repo: Path, item: dict, phase: str, **changes):
    review = q.review_template(item, phase)
    review.update(
        decision="APPROVE",
        finding="Exact-version Astra review accepts the next research gate.",
        next_action="Proceed to the bounded next gate only.",
    )
    review.update(changes)
    ref = q.expected_review_ref(item, phase)
    path = repo / ref
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(review))
    return path, review


def route_fixture(tmp_path):
    bridge = tmp_path / "bridge"
    routes = bridge / "routes"
    routes.mkdir(parents=True)
    config = bridge / "autobuild_control_route.json"
    config.write_text(json.dumps({
        "schema": "PREDICTION_AUTOBUILD_ROUTE_V1",
        "route_task_id": "SESSION-ROUTE-CANARY",
    }))
    (routes / "SESSION-ROUTE-CANARY.json").write_text(json.dumps({
        "version": 2,
        "task_id": "SESSION-ROUTE-CANARY",
        "chat_id": "chat-astra-canary-1234",
    }))
    return bridge, routes, config


def test_any_positive_net_euro_counts_but_zero_or_negative_does_not():
    assert q.economic_signal_counts(0.01) is True
    assert q.economic_signal_counts(1.0) is True
    assert q.economic_signal_counts(0.0) is False
    assert q.economic_signal_counts(-0.01) is False


def test_wrong_reviewer_model_fails_closed(tmp_path):
    item = overlay()
    _, review = write_review(tmp_path, item, "PREBUILD", reviewer_model="GPT-5.6 Sol")
    with pytest.raises(q.ReviewGateError, match="WRONG_MODEL"):
        q.validate_review(review, item, "PREBUILD")


def test_stale_astra_review_cannot_be_reused_after_candidate_change(tmp_path):
    item = overlay()
    _, review = write_review(tmp_path, item, "PREBUILD")
    changed = dict(item)
    changed["next_action"] = "Changed after review; old approval must expire."
    with pytest.raises(q.ReviewGateError, match="STALE_BINDING"):
        q.validate_review(review, changed, "PREBUILD")


def test_prebuild_astra_approval_unlocks_build_only(tmp_path):
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    states = runtime / "candidate_states"
    states.mkdir(parents=True)
    item = overlay()
    item["pending_build_handoff"] = {
        "status": "AWAITING_ASTRA_PREBUILD_REVIEW",
        "operation": "PROTOCOL_DEATHCHECK_VALIDATION",
        "protocol_refs": ["knowledge/candidates/protocols/p.json"],
    }
    path = states / "item.json"
    path.write_text(json.dumps(item))
    write_review(repo, item, "PREBUILD")

    updated, ref = q.apply_review(Supervisor(runtime), repo, path, "PREBUILD")
    assert updated["queue_status"] == "NEEDS_BUILD"
    assert updated["astra_reviews"]["PREBUILD"]["reviewer_model"] == "GPT-6 Astra"
    assert updated["build_handoff"]["status"] == "BUILD_TASK_QUEUED"
    assert updated["build_handoff"]["astra_prebuild_review_ref"] == ref
    assert "pending_build_handoff" not in updated


def test_premeasurement_astra_approval_allows_read_only_measurement_not_trading(tmp_path):
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    states = runtime / "candidate_states"
    states.mkdir(parents=True)
    item = overlay("ASTRA_PREMEASUREMENT_REVIEW")
    path = states / "item.json"
    path.write_text(json.dumps(item))
    write_review(repo, item, "PREMEASUREMENT")

    updated, ref = q.apply_review(Supervisor(runtime), repo, path, "PREMEASUREMENT")
    assert updated["queue_status"] == "MEASUREMENT_READY"
    auth = updated["measurement_authorization"]
    assert auth["authorized"] is True
    assert auth["scope"] == "READ_ONLY_PROSPECTIVE_MARKET_DATA"
    assert auth["order_submission"] is False
    assert auth["live_trading"] is False
    assert auth["astra_premeasurement_review_ref"] == ref


def test_astra_review_wake_requires_exact_model_and_small_profit_policy(tmp_path, monkeypatch):
    bridge, routes, config = route_fixture(tmp_path)
    monkeypatch.setattr(a, "BRIDGE_DATA", bridge)
    monkeypatch.setattr(a, "ROUTE_CONFIG", config)
    monkeypatch.setattr(a, "ROUTES", routes)
    item = overlay()
    s = Supervisor(tmp_path / "runtime")
    result = a.ensure_review_continuation(s, tmp_path / "repo", item, "PREBUILD")
    record = json.loads((bridge / "continuations" / f"{result['continuation_id']}.json").read_text())
    msg = record["context_message"]
    assert "required_model=GPT-6 Astra" in msg
    assert "minimum_net_profit_eur=0.0" in msg
    assert "strictly positive NET executable euro edge is worth testing" in msg


def test_measurement_wake_is_read_only_and_highest_gpt_builder(tmp_path, monkeypatch):
    bridge, routes, config = route_fixture(tmp_path)
    monkeypatch.setattr(mw, "BRIDGE_DATA", bridge)
    monkeypatch.setattr(mw, "ROUTE_CONFIG", config)
    monkeypatch.setattr(mw, "ROUTES", routes)
    item = overlay("MEASUREMENT_READY")
    item["measurement_authorization"] = {
        "authorized": True,
        "scope": "READ_ONLY_PROSPECTIVE_MARKET_DATA",
        "astra_premeasurement_review_ref": "knowledge/reviews/astra/r.json",
        "order_submission": False,
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
    }
    item["astra_reviews"] = {
        "PREMEASUREMENT": {
            "decision": "APPROVE",
            "reviewer_model": "GPT-6 Astra",
            "ref": "knowledge/reviews/astra/r.json",
        }
    }
    s = Supervisor(tmp_path / "runtime")
    result = mw.ensure_measurement_continuation(s, item)
    record = json.loads((bridge / "continuations" / f"{result['continuation_id']}.json").read_text())
    msg = record["context_message"]
    assert "required_builder_policy=HIGHEST_AVAILABLE_GPT" in msg
    assert "measurement_scope=READ_ONLY_PROSPECTIVE_MARKET_DATA" in msg
    assert "No orders" in msg
    audit = json.loads(next((s.root / "measurement_wakes").glob("*.json")).read_text())
    assert audit["minimum_net_profit_eur"] == 0.0
    assert audit["live_trading"] is False


def test_direct_measurement_wake_requires_astra_premeasurement_approval(tmp_path):
    s = Supervisor(tmp_path / "runtime")
    item = overlay("MEASUREMENT_READY")
    item["measurement_authorization"] = {
        "authorized": True,
        "scope": "READ_ONLY_PROSPECTIVE_MARKET_DATA",
        "astra_premeasurement_review_ref": "knowledge/reviews/astra/r.json",
        "order_submission": False,
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
    }
    with pytest.raises(mw.MeasurementWakeBlocked, match="ASTRA_PREMEASUREMENT_APPROVAL_REQUIRED"):
        mw.ensure_measurement_continuation(s, item)


def test_measurement_wake_rejects_any_order_or_live_path(tmp_path):
    s = Supervisor(tmp_path / "runtime")
    item = overlay("MEASUREMENT_READY")
    item["measurement_authorization"] = {
        "authorized": True,
        "scope": "READ_ONLY_PROSPECTIVE_MARKET_DATA",
        "astra_premeasurement_review_ref": "knowledge/reviews/astra/r.json",
        "order_submission": True,
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
    }
    with pytest.raises(mw.MeasurementWakeBlocked, match="ORDER_PATH_FORBIDDEN"):
        mw.ensure_measurement_continuation(s, item)
