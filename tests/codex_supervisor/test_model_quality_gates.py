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


def overlay(state="ASTRA_PREBUILD_REVIEW", qualification_fixture=False):
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
            "qualification_fixture": qualification_fixture,
        },
        "qualification_fixture": qualification_fixture,
        "referenced_evidence": {
            "knowledge/evidence/x.json": "{\"net_candidate_eur\":0.01}",
        },
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "remote_push": False,
    }


def write_attestation(
    repo: Path,
    route_task_id="SESSION-ROUTE-CANARY",
    usage_scope=q.MODEL_PROVENANCE_PRODUCTION_SCOPE,
    **changes,
):
    method = (
        q.MODEL_PROVENANCE_TEST_METHOD
        if usage_scope == q.MODEL_PROVENANCE_TEST_SCOPE
        else q.MODEL_PROVENANCE_PRODUCTION_METHOD
    )
    value = {
        "schema": q.MODEL_PROVENANCE_SCHEMA,
        "route_task_id": route_task_id,
        "reviewer_model": "GPT-6 Astra",
        "reviewer_role": "INDEPENDENT_GATE_REVIEWER",
        "verification_method": method,
        "attestation_scope": "ROUTE",
        "usage_scope": usage_scope,
        "attested_by": "TEST_OPERATOR",
        "attested_at": "2026-10-05T00:00:00Z",
        "revoked": False,
    }
    value.update(changes)
    ref = q.expected_model_provenance_ref(route_task_id)
    path = repo / ref
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))
    return ref, value, q.canonical_sha(value)


def write_review(repo: Path, item: dict, phase: str, route_task_id="SESSION-ROUTE-CANARY", **changes):
    provenance_ref, _, provenance_sha = write_attestation(repo, route_task_id)
    review = q.review_template(
        item,
        phase,
        route_task_id=route_task_id,
        model_provenance_ref=provenance_ref,
        model_provenance_sha256=provenance_sha,
    )
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
        q.validate_review(review, item, "PREBUILD", repo=tmp_path)


def test_missing_external_model_provenance_fails_closed(tmp_path):
    item = overlay()
    path, _ = write_review(tmp_path, item, "PREBUILD")
    provenance = tmp_path / q.expected_model_provenance_ref("SESSION-ROUTE-CANARY")
    provenance.unlink()
    with pytest.raises(q.ReviewGateError, match="PROVENANCE_MISSING"):
        q.load_review(tmp_path, item, "PREBUILD")
    assert path.exists()


def test_review_route_must_match_attested_route(tmp_path):
    item = overlay()
    _, review = write_review(tmp_path, item, "PREBUILD")
    review["reviewer_route_task_id"] = "SESSION-ROUTE-OTHER"
    with pytest.raises(q.ReviewGateError, match="PROVENANCE_MISSING"):
        q.validate_review(review, item, "PREBUILD", repo=tmp_path)



def test_manual_test_only_attestation_is_rejected_for_production_candidate(tmp_path):
    item = overlay(qualification_fixture=False)
    route = "SESSION-ROUTE-CANARY"
    ref, _, sha = write_attestation(
        tmp_path,
        route,
        usage_scope=q.MODEL_PROVENANCE_TEST_SCOPE,
    )
    review = q.review_template(
        item,
        "PREBUILD",
        route_task_id=route,
        model_provenance_ref=ref,
        model_provenance_sha256=sha,
    )
    review.update(
        decision="APPROVE",
        finding="Should not authorize production.",
        next_action="Must fail closed.",
    )
    with pytest.raises(q.ReviewGateError, match="TEST_ONLY_PROVENANCE_FORBIDDEN_IN_PRODUCTION"):
        q.validate_review(review, item, "PREBUILD", repo=tmp_path)


def test_stale_astra_review_cannot_be_reused_after_candidate_change(tmp_path):
    item = overlay()
    _, review = write_review(tmp_path, item, "PREBUILD")
    changed = dict(item)
    changed["next_action"] = "Changed after review; old approval must expire."
    with pytest.raises(q.ReviewGateError, match="STALE_BINDING"):
        q.validate_review(review, changed, "PREBUILD", repo=tmp_path)


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
    gate = updated["astra_reviews"]["PREBUILD"]
    assert gate["reviewer_model"] == "GPT-6 Astra"
    assert gate["reviewer_route_task_id"] == "SESSION-ROUTE-CANARY"
    assert gate["model_provenance_ref"] == q.expected_model_provenance_ref("SESSION-ROUTE-CANARY")
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


def test_astra_review_wake_uses_external_route_provenance_and_small_profit_policy(tmp_path, monkeypatch):
    bridge, routes, config = route_fixture(tmp_path)
    monkeypatch.setattr(a, "BRIDGE_DATA", bridge)
    monkeypatch.setattr(a, "ROUTE_CONFIG", config)
    monkeypatch.setattr(a, "ROUTES", routes)
    item = overlay(qualification_fixture=True)
    repo = tmp_path / "repo"
    write_attestation(repo, usage_scope=q.MODEL_PROVENANCE_TEST_SCOPE)
    s = Supervisor(tmp_path / "runtime")
    result = a.ensure_review_continuation(s, repo, item, "PREBUILD")
    record = json.loads((bridge / "continuations" / f"{result['continuation_id']}.json").read_text())
    msg = record["context_message"]
    assert "required_model=GPT-6 Astra" in msg
    assert "model_identity_verification=EXTERNAL_ROUTE_ATTESTATION_TEST_ONLY" in msg
    assert "do not self-attest your model identity" in msg.lower()
    assert "minimum_net_profit_eur=0.0" in msg
    assert "strictly positive NET executable euro edge is worth testing" in msg
    assert result["control_route_task_id"] == "SESSION-ROUTE-CANARY"
    assert result["model_provenance_ref"] == q.expected_model_provenance_ref("SESSION-ROUTE-CANARY")


def test_astra_review_wake_fails_without_attested_route(tmp_path, monkeypatch):
    bridge, routes, config = route_fixture(tmp_path)
    monkeypatch.setattr(a, "BRIDGE_DATA", bridge)
    monkeypatch.setattr(a, "ROUTE_CONFIG", config)
    monkeypatch.setattr(a, "ROUTES", routes)
    with pytest.raises(a.AstraReviewWakeBlocked, match="MODEL_PROVENANCE"):
        a.ensure_review_continuation(
            Supervisor(tmp_path / "runtime"),
            tmp_path / "repo",
            overlay(qualification_fixture=True),
            "PREBUILD",
        )


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
    repo = tmp_path / "repo"
    provenance_ref, _, provenance_sha = write_attestation(repo)
    review = q.review_template(
        item,
        "PREMEASUREMENT",
        route_task_id="SESSION-ROUTE-CANARY",
        model_provenance_ref=provenance_ref,
        model_provenance_sha256=provenance_sha,
    )
    review.update(
        decision="APPROVE",
        finding="Fixture Astra approves exact premeasurement binding.",
        next_action="Proceed to read-only prospective measurement only.",
    )
    ref = q.expected_review_ref(item, "PREMEASUREMENT")
    review_path = repo / ref
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(json.dumps(review))
    item["measurement_authorization"]["astra_premeasurement_review_ref"] = ref
    item["astra_reviews"] = {
        "PREMEASUREMENT": {
            "decision": "APPROVE",
            "reviewer_model": "GPT-6 Astra",
            "reviewer_route_task_id": "SESSION-ROUTE-CANARY",
            "model_provenance_ref": provenance_ref,
            "model_provenance_sha256": provenance_sha,
            "ref": ref,
        }
    }
    s = Supervisor(tmp_path / "runtime")
    result = mw.ensure_measurement_continuation(s, item, repo=repo)
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
