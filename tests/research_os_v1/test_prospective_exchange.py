import copy

import pytest

from control.research_os_v1.prospective_exchange import (
    build_exchange_shadow_bundle,
    select_challenger_roles,
)


def packet(role, candidate_ids=None):
    return {
        "agent_id": role,
        "candidate_ids": candidate_ids or [],
        "input_refs": [f"knowledge/runs/{role}.json"],
        "routed_evidence": [],
        "priority": "P2",
        "status": "READY",
    }


def work_item(role, candidate_ids=None):
    return {
        "agent_id": role,
        "legacy_role": role,
        "capability_mode": "TEST",
        "responsibility": role.upper(),
        "must_return_result": True,
        "objective": f"test {role}",
        "packet": packet(role, candidate_ids),
    }


def telemetry(role, evidence_id=None, *, relevant=True):
    eid = evidence_id or f"source_registry:{role}:abc"
    return {
        "worker_run_id": f"hourly-20260922T100000+0200:{role}",
        "research_items": [{"item_id": f"R:{role}", "duplicate_of": None}],
        "evidence": [{
            "evidence_id": eid,
            "source_family": "OFFICIAL",
            "relevant": relevant,
            "contradiction": False,
            "point_in_time_ok": True,
            "provenance_ok": True,
        }],
        "failure_patterns": [],
        "queue_starvation_event_ids": [],
    }


def role_result(role, candidate_ids=None, *, status="COMPLETED", evidence_id=None, relevant=True):
    return {
        "agent_id": role,
        "status": status,
        "finding": "finding",
        "evidence_refs": [evidence_id or f"source_registry:{role}:abc"],
        "candidate_ids": candidate_ids or [],
        "next_decisive_question": None,
        "local_task_required": False,
        "local_task_spec": None,
        "benchmark_telemetry": telemetry(role, evidence_id, relevant=relevant),
    }


def request():
    roles = [
        work_item("recon_scout"),
        work_item("scout"),
        work_item("algebra", ["C1"]),
        work_item("settlement", ["C2"]),
        work_item("research_director"),
    ]
    return {
        "schema": "PVA_AI_EXCHANGE_REQUEST_V1",
        "run_id": "hourly-20260922T100000+0200",
        "request_sha256": "REQHASH",
        "response_token": "TOKEN",
        "source_commit": "abc123",
        "governor": {
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
            "openai_api": False,
        },
        "work_items": roles,
    }


def response():
    results = [
        role_result("recon_scout"),
        role_result("scout"),
        role_result("algebra", ["C1"]),
        role_result("settlement", ["C2"]),
        role_result("research_director"),
    ]
    return {
        "schema": "PVA_AI_EXCHANGE_RESPONSE_V1",
        "run_id": "hourly-20260922T100000+0200",
        "request_sha256": "REQHASH",
        "response": {
            "schema": "PVA_AI_RESPONSE_V1",
            "run_id": "hourly-20260922T100000+0200",
            "response_token": "TOKEN",
            "role_results": results,
            "candidate_decisions": [],
            "economic_conclusion": "NO_PROVEN_EDGE",
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
            "openai_api": False,
        },
    }


def candidates():
    return [
        {
            "candidate_id": "C1",
            "hypothesis": "h1",
            "phase": "DISCOVERED",
            "queue_status": "NEEDS_DIRECTOR",
            "priority": "P2",
            "required_gates": {},
        },
        {
            "candidate_id": "C2",
            "hypothesis": "h2",
            "phase": "MECHANISM_DEFINED",
            "queue_status": "RUNNING",
            "priority": "P1",
            "required_gates": {},
        },
    ]


def test_low_usage_selection_is_pre_response_and_bounded():
    selected = select_challenger_roles(request())
    assert "scout" in selected
    assert "recon_scout" in selected
    assert "research_director" in selected
    assert len(selected) == 4
    assert len(set(selected) & {"algebra", "settlement"}) == 1


def test_exchange_bundle_preserves_all_pre_run_candidate_cases():
    out = build_exchange_shadow_bundle(request(), response(), candidates())
    assert out["cycle_capture"]["case_count"] == 2
    assert len(out["baseline_records"]) == 2
    assert len(out["challenger_records"]) == 2
    assert out["economic_conclusion"] == "NO_PROVEN_EDGE"
    by_candidate = {row["candidate_id"]: row for row in out["challenger_records"]}
    # Settlement outranks algebra in the frozen ordinal task ranking, so C1 is
    # intentionally not assigned rather than silently dropped.
    assert by_candidate["C1"]["intentionally_unassigned"] is True
    assert by_candidate["C1"]["worker_run_ids"] == []
    assert by_candidate["C2"]["intentionally_unassigned"] is False


def test_request_response_hash_mismatch_fails_closed():
    bad = response()
    bad["request_sha256"] = "OTHER"
    with pytest.raises(ValueError, match="exchange_request_sha256_mismatch"):
        build_exchange_shadow_bundle(request(), bad, candidates())


def test_missing_benchmark_telemetry_fails_closed():
    bad = response()
    del bad["response"]["role_results"][0]["benchmark_telemetry"]
    with pytest.raises(ValueError, match="benchmark_telemetry_missing"):
        build_exchange_shadow_bundle(request(), bad, candidates())


def test_candidate_link_missing_in_response_fails_closed():
    bad = response()
    for result in bad["response"]["role_results"]:
        if result["agent_id"] == "algebra":
            result["candidate_ids"] = []
    with pytest.raises(ValueError, match="candidate_link_missing_in_result:C1:algebra"):
        build_exchange_shadow_bundle(request(), bad, candidates())


def test_transport_self_reference_cannot_count_as_relevant_evidence():
    bad = response()
    for result in bad["response"]["role_results"]:
        if result["agent_id"] == "settlement":
            result["benchmark_telemetry"] = telemetry(
                "settlement",
                "ai_exchange/requests/hourly-20260922T100000+0200.json#settlement",
                relevant=True,
            )
    with pytest.raises(ValueError, match="transport_self_reference_must_be_irrelevant"):
        build_exchange_shadow_bundle(request(), bad, candidates())


def test_role_coverage_must_exactly_match_request():
    bad = response()
    bad["response"]["role_results"].pop()
    with pytest.raises(ValueError, match="role_coverage_mismatch"):
        build_exchange_shadow_bundle(request(), bad, candidates())


def test_forbidden_response_flag_fails_closed():
    bad = response()
    bad["response"]["wallet_actions"] = True
    with pytest.raises(ValueError, match="forbidden_response_flag:wallet_actions"):
        build_exchange_shadow_bundle(request(), bad, candidates())
