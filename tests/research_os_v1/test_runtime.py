from control.research_os_v1.governor import classify
from control.research_os_v1.failure_memory import required_checks, UnknownFailurePattern
from control.research_os_v1.evidence_graph import EvidenceGraph
from control.research_os_v1.candidate_view import canonicalize
from control.research_os_v1.contracts import validate_task
from control.research_os_v1.scheduler import fanout_cap, schedule
from control.research_os_v1.shadow_cycle import build_shadow_plan


def base_task(task_id="T1", parallelism="HIGH", dependency="INDEPENDENT"):
    return {
        "task_id": task_id,
        "worker_domain": "discovery",
        "objective": "find new evidence",
        "task_shape": {
            "parallelism": parallelism,
            "dependency_shape": dependency,
            "uncertainty_type": "SOURCE",
            "time_sensitivity": "HIGH",
            "novelty": "NOVEL",
            "decision_relevance": "HIGH",
        },
        "inputs": {"failure_pattern_ids": ["FP-004"]},
        "constraints": {"live_trading": False, "paid_actions": False, "wallet_actions": False, "source_policy": "FREE_PUBLIC_ONLY"},
        "expected_output": {"artifact_type": "DISCOVERY_FINDING", "required_fields": ["evidence"]},
        "scheduling": {
            "uncertainty_reduction": "HIGH",
            "dependency_unlock_value": "MULTIPLE",
            "evidence_cost": "LOW",
            "model_cost": "MEDIUM",
            "duplication_risk": "LOW",
        },
    }


def test_governor_allows_only_structured_free_research():
    d = classify({"kind": "free_public_read_only_research", "provenance": True, "point_in_time": True})
    assert d.admissible is True
    assert classify({"kind": "free_public_read_only_research", "provenance": False, "point_in_time": True}).admissible is False


def test_governor_requires_approval_for_paid_and_live():
    assert classify({"kind": "paid_action"}).requires_user_approval is True
    assert classify({"kind": "live_order_or_trade"}).requires_user_approval is True
    assert classify({"kind": "wallet_or_fund_movement"}).requires_user_approval is True


def test_unknown_action_fails_closed():
    d = classify({"kind": "magic_unknown_action"})
    assert d.admissible is False


def test_failure_memory_returns_checks_not_kills():
    rows = required_checks(["FP-004", "FP-004"])
    assert len(rows) == 1
    assert rows[0]["automatic_kill"] is False
    try:
        required_checks(["FP-NOPE"])
        assert False
    except UnknownFailurePattern:
        pass


def test_candidate_adapter_is_read_only_and_fail_closed():
    src = {"candidate_id": "C1", "hypothesis": "x", "gates": {"mechanism": "PASS"}, "decision": "UNPROVEN"}
    out = canonicalize(src, source_commit="abc123")
    assert out["economic_status"] == "NO_PROVEN_EDGE"
    assert out["required_gates"]["mechanism"] == "PASS"
    assert out["required_gates"]["execution_reality"] == "PENDING"
    assert "version" not in src


def test_evidence_graph_is_idempotent_and_rejects_conflict():
    g = EvidenceGraph()
    n = {"id":"c1","type":"candidate","status":"ACTIVE","created_at":"2026-01-01T00:00:00Z","producer":"test"}
    g.add_node(n); g.add_node(n)
    e = {"id":"e1","type":"evidence","status":"OK","created_at":"2026-01-01T00:00:00Z","producer":"test"}
    g.add_node(e)
    edge={"from":"e1","to":"c1","type":"supports","created_at":"2026-01-01T00:00:00Z","producer":"test"}
    g.add_edge(edge); g.add_edge(edge)
    assert len(g.as_dict()["nodes"]) == 2
    assert len(g.as_dict()["edges"]) == 1


def test_worker_contract_rejects_money_flags():
    t = base_task()
    assert validate_task(t) == []
    t["constraints"]["paid_actions"] = True
    assert "paid_actions_must_be_false" in validate_task(t)


def test_scheduler_caps_sequential_and_ranks_decisive():
    assert fanout_cap(base_task(parallelism="LOW", dependency="SEQUENTIAL")) == 1
    a = base_task("A")
    b = base_task("B")
    b["task_shape"]["decision_relevance"] = "DECISIVE"
    assert schedule([a,b])["selected"][0] == "B"


def test_shadow_cycle_never_mutates_or_promotes():
    candidate = {"candidate_id":"C1","hypothesis":"h","decision":"UNPROVEN","gates":{}}
    t = base_task()
    out = build_shadow_plan([candidate], [t], source_commit="deadbeef")
    assert out["mode"] == "SHADOW_READ_ONLY"
    assert out["runtime_mutation"] is False
    assert out["live_trading"] is False
    assert out["economic_conclusion"] == "NO_PROVEN_EDGE"
    assert out["scheduled"]["selected"] == ["T1"]
    assert out["scheduled"]["tasks"][0]["fanout_cap"] == 5
