from pathlib import Path
import importlib.util
import json
import sys
import types
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control/codex_supervisor"))
import build_wake as b
import model_quality_gate as q


class Supervisor:
    def __init__(self, root):
        self.root = root


def overlay(approved=True):
    item = {
        "candidate_id": "CANARY",
        "queue_status": "NEEDS_BUILD",
        "source_hashes": {"knowledge/candidates/CANARY.json": "a" * 64},
        "originating_task_id": "CANDIDATE-CANARY-v1",
        "completion_hash": "b" * 64,
        "finding": "Een kleine collector ontbreekt.",
        "next_action": "Bouw een bounded read-only collector en test die.",
        "candidate_snapshot": {
            "candidate_id": "CANARY",
            "prospective_protocols": [],
        },
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
    }
    if approved:
        item["astra_reviews"] = {
            "PREBUILD": {
                "decision": "APPROVE",
                "reviewer_model": "GPT-6 Astra",
                "ref": "knowledge/reviews/astra/canary-prebuild.json",
            }
        }
    return item


def canonical_prebuild_review(tmp_path, item):
    repo = tmp_path / "repo"
    binding = q.review_binding(item, "PREBUILD")
    slug = "gpt-6-astra-test"
    source_task_id = "ASTRA-AUTO-REVIEW-TEST"
    completion_sha = "d" * 64
    provenance = {
        "schema": q.AUTONOMOUS_PROVENANCE_SCHEMA,
        "usage_scope": q.MODEL_PROVENANCE_PRODUCTION_SCOPE,
        "verification_method": q.MODEL_PROVENANCE_PRODUCTION_METHOD,
        "reviewer_model": "GPT-6 Astra",
        "reviewer_role": "INDEPENDENT_GATE_REVIEWER",
        "reviewer_model_slug": slug,
        "model_policy": "ASTRA_EXACT",
        "visible_astra_count": 1,
        "candidate_id": item["candidate_id"],
        "phase": "PREBUILD",
        "binding_sha256": binding,
        "source_task_id": source_task_id,
        "input_sha256": "e" * 64,
        "completion_sha256": completion_sha,
        "worker_record_sha256": "f" * 64,
        "model_selection": {
            "policy": "ASTRA_EXACT",
            "visible_astra_count": 1,
            "selected_slug": slug,
        },
    }
    provenance_ref = q.expected_autonomous_provenance_ref(item, "PREBUILD")
    provenance_path = repo / provenance_ref
    provenance_path.parent.mkdir(parents=True, exist_ok=True)
    provenance_path.write_text(json.dumps(provenance))
    review = {
        "schema": q.SCHEMA,
        "candidate_id": item["candidate_id"],
        "phase": "PREBUILD",
        "binding_sha256": binding,
        "reviewer_model": "GPT-6 Astra",
        "reviewer_role": "INDEPENDENT_GATE_REVIEWER",
        "provenance_kind": q.PROVENANCE_AUTONOMOUS_RUN,
        "reviewer_model_slug": slug,
        "source_task_id": source_task_id,
        "completion_sha256": completion_sha,
        "model_provenance_ref": provenance_ref,
        "model_provenance_sha256": q.canonical_sha(provenance),
        "decision": "APPROVE",
        "finding": "Fixture autonomous Astra approves exact prebuild binding.",
        "next_action": "Proceed to bounded build only.",
        "economic_policy": q.ECONOMIC_POLICY,
        "minimum_net_profit_eur": 0.0,
        "measurement_scope": "READ_ONLY_PROSPECTIVE_MARKET_DATA",
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
    }
    ref = q.expected_review_ref(item, "PREBUILD")
    path = repo / ref
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(review))
    item.setdefault("astra_reviews", {})["PREBUILD"] = {
        "decision": "APPROVE",
        "reviewer_model": "GPT-6 Astra",
        "reviewer_model_slug": slug,
        "provenance_kind": q.PROVENANCE_AUTONOMOUS_RUN,
        "model_provenance_ref": provenance_ref,
        "model_provenance_sha256": q.canonical_sha(provenance),
        "ref": ref,
    }
    return repo


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
        "chat_id": "chat-canary-1234",
        "consumer_id": "consumer-canary-1234",
    }))
    return bridge, routes, config


def test_generic_needs_build_creates_one_external_continuation_and_audit(tmp_path):
    bridge, routes, config = route_fixture(tmp_path)
    s = Supervisor(tmp_path / "runtime")
    item = overlay()
    repo = canonical_prebuild_review(tmp_path, item)
    result = b.ensure_build_continuation(
        s,
        item,
        bridge_data=bridge,
        route_config=config,
        routes_dir=routes,
        repo=repo,
    )
    again = b.ensure_build_continuation(
        s,
        item,
        bridge_data=bridge,
        route_config=config,
        routes_dir=routes,
        repo=repo,
    )
    assert again == result
    assert result["continuation_state"] == "CONTINUE_REQUESTED"
    continuation = json.loads((bridge / "continuations" / f"{result['continuation_id']}.json").read_text())
    assert continuation["external_source_kind"] == "AUTOBUILD"
    assert continuation["expected_route_task_id"] == "SESSION-ROUTE-CANARY"
    assert "candidate_id=CANARY" in continuation["context_message"]
    audits = list((s.root / "autobuild_wakes").glob("*.json"))
    assert len(audits) == 1
    audit = json.loads(audits[0].read_text())
    assert audit["scientific_status"] == "NO_PROVEN_EDGE"
    assert audit["required_builder_policy"] == "HIGHEST_AVAILABLE_GPT"
    assert audit["economic_policy"] == "ANY_POSITIVE_NET_EDGE_COUNTS"
    assert audit["minimum_net_profit_eur"] == 0.0
    assert audit["live_trading"] is False


def test_direct_build_wake_requires_astra_prebuild_approval(tmp_path):
    bridge, routes, config = route_fixture(tmp_path)
    s = Supervisor(tmp_path / "runtime")
    with pytest.raises(b.BuildWakeBlocked, match="ASTRA_PREBUILD_APPROVAL_REQUIRED"):
        b.ensure_build_continuation(
            s,
            overlay(approved=False),
            bridge_data=bridge,
            route_config=config,
            routes_dir=routes,
        )


def test_autobuild_route_and_safety_fail_closed(tmp_path):
    s = Supervisor(tmp_path / "runtime")
    item = overlay()
    repo = canonical_prebuild_review(tmp_path, item)
    with pytest.raises(b.BuildWakeBlocked, match="ROUTE_CONFIG_MISSING"):
        b.ensure_build_continuation(
            s,
            item,
            bridge_data=tmp_path / "bridge",
            route_config=tmp_path / "missing.json",
            routes_dir=tmp_path / "routes",
            repo=repo,
        )
    bridge, routes, config = route_fixture(tmp_path)
    unsafe = overlay()
    unsafe["live_trading"] = True
    with pytest.raises(b.BuildWakeBlocked, match="UNSAFE_FLAGS"):
        b.ensure_build_continuation(
            s,
            unsafe,
            bridge_data=bridge,
            route_config=config,
            routes_dir=routes,
            repo=repo,
        )


def test_protocol_builds_stay_on_fixed_validator_path(tmp_path):
    bridge, routes, config = route_fixture(tmp_path)
    s = Supervisor(tmp_path / "runtime")
    item = overlay()
    item["candidate_snapshot"]["prospective_protocols"] = ["knowledge/candidates/protocols/p.json"]
    repo = canonical_prebuild_review(tmp_path, item)
    with pytest.raises(b.BuildWakeBlocked, match="PROTOCOL_PATH"):
        b.ensure_build_continuation(
            s,
            item,
            bridge_data=bridge,
            route_config=config,
            routes_dir=routes,
            repo=repo,
        )


def test_candidate_dispatch_legacy_needs_build_cannot_bypass_astra(tmp_path, monkeypatch):
    import hashlib
    import candidate_dispatch as d
    runtime = tmp_path / "runtime"
    states = runtime / "candidate_states"
    states.mkdir(parents=True)
    repo = tmp_path / "repo"
    source = repo / "knowledge/candidates/CANARY.json"
    source.parent.mkdir(parents=True)
    source.write_text('{"candidate_id":"CANARY","version":1}')
    item = overlay(approved=False)
    item["source_hashes"] = {
        "knowledge/candidates/CANARY.json": hashlib.sha256(source.read_bytes()).hexdigest()
    }
    item["finding"] = "generic build needed"
    item["next_action"] = "build bounded collector"
    path = states / "generic.json"
    path.write_text(json.dumps(item))

    class S:
        def __init__(self, root):
            self.root = root

    monkeypatch.setattr(d, "pending_validation_task", lambda *args, **kwargs: None)
    monkeypatch.setattr(d, "select_task", lambda *args, **kwargs: None)
    result = d.select_next(S(runtime), repo)
    assert result["queue_blocked"] is True
    assert result["reason"] == "ASTRA_PREBUILD_REVIEW_REQUIRED"
    migrated = json.loads(path.read_text())
    assert migrated["queue_status"] == "ASTRA_PREBUILD_REVIEW"


def test_stale_approved_overlay_cannot_retrigger_build_after_source_change(tmp_path, monkeypatch):
    import hashlib
    import candidate_dispatch as d
    runtime = tmp_path / "runtime"
    states = runtime / "candidate_states"
    states.mkdir(parents=True)
    repo = tmp_path / "repo"
    source = repo / "knowledge/candidates/CANARY.json"
    source.parent.mkdir(parents=True)
    source.write_text('{"candidate_id":"CANARY","version":1}')
    old_hash = hashlib.sha256(source.read_bytes()).hexdigest()

    item = overlay()
    item["source_hashes"] = {"knowledge/candidates/CANARY.json": old_hash}
    (states / "generic.json").write_text(json.dumps(item))
    source.write_text('{"candidate_id":"CANARY","version":2}')

    class S:
        def __init__(self, root):
            self.root = root

    monkeypatch.setattr(d, "pending_validation_task", lambda *args, **kwargs: None)
    monkeypatch.setattr(d, "select_task", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        b,
        "ensure_build_continuation",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("stale overlay triggered build")),
    )
    assert d.select_next(S(runtime), repo) is None


def test_candidate_dispatch_astra_approved_needs_build_routes_to_chat_wake(tmp_path, monkeypatch):
    import hashlib
    import candidate_dispatch as d
    runtime = tmp_path / "runtime"
    states = runtime / "candidate_states"
    states.mkdir(parents=True)
    repo = tmp_path / "repo"
    source = repo / "knowledge/candidates/CANARY.json"
    source.parent.mkdir(parents=True)
    source.write_text('{"candidate_id":"CANARY","version":1}')
    item = overlay()
    item["source_hashes"] = {
        "knowledge/candidates/CANARY.json": hashlib.sha256(source.read_bytes()).hexdigest()
    }
    repo = canonical_prebuild_review(tmp_path, item)
    path = states / "generic.json"
    path.write_text(json.dumps(item))

    class S:
        def __init__(self, root):
            self.root = root

    monkeypatch.setattr(d, "pending_validation_task", lambda *args, **kwargs: None)
    monkeypatch.setattr(d, "select_task", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        b,
        "ensure_build_continuation",
        lambda supervisor, candidate, **kwargs: {
            "continuation_id": "CONT-1234567890abcdef12345678",
            "continuation_state": "CONTINUE_REQUESTED",
        },
    )
    result = d.select_next(S(runtime), repo)
    assert result["queue_blocked"] is True
    assert result["reason"] == "AUTOBUILD_CHAT_WAKE_QUEUED"
    assert result["continuation_id"] == "CONT-1234567890abcdef12345678"
