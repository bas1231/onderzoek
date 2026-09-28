from control.research_os_v1.governor import classify
from control.research_os_v1.failure_memory import required_checks, UnknownFailurePattern
from control.research_os_v1.evidence_graph import EvidenceGraph
from control.research_os_v1.candidate_view import canonicalize
from control.research_os_v1.contracts import validate_task
from control.research_os_v1.scheduler import fanout_cap, schedule
from control.research_os_v1.shadow_cycle import build_shadow_plan
from control.research_os_v1.legacy_adapter import packet_to_task
from control.research_os_v1.shadow_cli import build_from_paths
from control.research_os_v1.hypothesis_accounting import adaptive_search_flags
from control.research_os_v1.discovery_coverage import summarize as summarize_coverage
from control.research_os_v1.promotion import evaluate as evaluate_promotion
from control.research_os_v1.resurrection import evaluate as evaluate_resurrection
from control.research_os_v1.red_team import build_blind_packet
from control.research_os_v1.reproducer import source_independence
from control.research_os_v1.shadow_benchmark import summarize as summarize_benchmark, replacement_check
import json


def base_task(task_id="T1", parallelism="HIGH", dependency="INDEPENDENT"):
    return {
        "task_id": task_id,
        "worker_domain": "discovery",
        "objective": "find new evidence",
        "state": "READY",
        "task_shape": {
            "parallelism": parallelism,
            "dependency_shape": dependency,
            "uncertainty_type": "SOURCE",
            "time_sensitivity": "HIGH",
            "novelty": "NOVEL",
            "decision_relevance": "HIGH",
        },
        "inputs": {"failure_pattern_ids": ["FP-004"]},
        "constraints": {
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
            "source_policy": "FREE_PUBLIC_ONLY",
        },
        "expected_output": {
            "artifact_type": "DISCOVERY_FINDING",
            "required_fields": ["evidence"],
        },
        "scheduling": {
            "uncertainty_reduction": "HIGH",
            "dependency_unlock_value": "MULTIPLE",
            "evidence_cost": "LOW",
            "model_cost": "MEDIUM",
            "duplication_risk": "LOW",
        },
        "proposed_action": {
            "kind": "free_public_read_only_research",
            "provenance": True,
            "point_in_time": True,
        },
    }


def promotion_candidate(signal_state="PASS"):
    gates = {
        g: "PASS"
        for g in [
            "source_provenance",
            "point_in_time",
            "mechanism",
            "signal_edge",
            "market_edge",
            "execution_reality",
            "prebuild_killer",
            "chief_falsifier",
            "validation",
            "independent_reproduction",
            "shadow",
        ]
    }
    gates["signal_edge"] = signal_state
    return {"required_gates": gates}


def benchmark_rows(*, better=False, case_prefix="CASE"):
    rows = []
    for i in range(20):
        cls = "SURVIVOR" if i == 0 else "DECISIVE_NEGATIVE"
        rows.append({
            "case_id": f"{case_prefix}-{i:02d}",
            "active_hour_id": f"H{i // 2}",
            "task_shape": "PARALLEL" if i % 2 else "SEQUENTIAL",
            "ground_truth_class": cls,
            "decision": "KEEP" if cls == "SURVIVOR" else "KILL",
            "worker_runs": 2,
            "unique_relevant_evidence": 3 if better else 2,
            "research_items": 3,
            "duplicate_research_items": 0 if better else 1,
            "contradictions_found": 1,
            "applicable_known_failure_patterns": 1,
            "failure_patterns_before_expensive_work": 1,
            "point_in_time_and_provenance_complete": True,
            "queue_starvation_events": 0,
            "steps_to_decisive_falsification": 2,
            "source_families_covered": ["OFFICIAL", "CODE"],
            "hard_failures": [],
        })
    return rows


def test_governor_allows_only_structured_free_research():
    d = classify({
        "kind": "free_public_read_only_research",
        "provenance": True,
        "point_in_time": True,
    })
    assert d.admissible is True
    assert classify({
        "kind": "free_public_read_only_research",
        "provenance": False,
        "point_in_time": True,
    }).admissible is False


def test_governor_requires_approval_for_paid_and_live():
    assert classify({"kind": "paid_action"}).requires_user_approval is True
    assert classify({"kind": "live_order_or_trade"}).requires_user_approval is True
    assert classify({"kind": "wallet_or_fund_movement"}).requires_user_approval is True


def test_unknown_action_fails_closed():
    assert classify({"kind": "magic_unknown_action"}).admissible is False


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
    src = {
        "candidate_id": "C1",
        "hypothesis": "x",
        "gates": {"mechanism": "PASS"},
        "decision": "UNPROVEN",
    }
    out = canonicalize(src, source_commit="abc123")
    assert out["economic_status"] == "NO_PROVEN_EDGE"
    assert out["required_gates"]["mechanism"] == "PASS"
    assert out["required_gates"]["execution_reality"] == "PENDING"
    assert "version" not in src


def test_candidate_adapter_preserves_existing_canonical_gates():
    src = {
        "candidate_id": "C2",
        "hypothesis": "x",
        "required_gates": {
            "mechanism": "PASS",
            "execution_reality": "FAIL",
        },
        "economic_status": "NO_PROVEN_EDGE",
    }
    out = canonicalize(src, source_commit="abc123")
    assert out["required_gates"]["mechanism"] == "PASS"
    assert out["required_gates"]["execution_reality"] == "FAIL"


def test_candidate_adapter_preserves_closed_negative_without_decision():
    out = canonicalize({
        "candidate_id": "C3",
        "hypothesis": "x",
        "queue_status": "CLOSED_NEGATIVE",
        "required_gates": {},
    }, source_commit="abc123")
    assert out["economic_status"] == "TESTED_NEGATIVE"


def test_evidence_graph_is_idempotent_and_rejects_conflict():
    g = EvidenceGraph()
    n = {"id": "c1", "type": "candidate", "status": "ACTIVE", "created_at": "2026-01-01T00:00:00Z", "producer": "test"}
    g.add_node(n)
    g.add_node(n)
    e = {"id": "e1", "type": "evidence", "status": "OK", "created_at": "2026-01-01T00:00:00Z", "producer": "test"}
    g.add_node(e)
    edge = {"from": "e1", "to": "c1", "type": "supports", "created_at": "2026-01-01T00:00:00Z", "producer": "test"}
    g.add_edge(edge)
    g.add_edge(edge)
    assert len(g.as_dict()["nodes"]) == 2
    assert len(g.as_dict()["edges"]) == 1


def test_worker_contract_rejects_money_flags():
    t = base_task()
    assert validate_task(t) == []
    t["constraints"]["paid_actions"] = True
    assert "paid_actions_must_be_false" in validate_task(t)


def test_worker_contract_requires_explicit_action_and_state():
    t = base_task()
    t.pop("proposed_action")
    assert "proposed_action_kind_required" in validate_task(t)
    t = base_task()
    t.pop("state")
    assert "invalid_task_state" in validate_task(t)


def test_scheduler_caps_sequential_and_ranks_decisive():
    assert fanout_cap(base_task(parallelism="LOW", dependency="SEQUENTIAL")) == 1
    a = base_task("A")
    b = base_task("B")
    b["task_shape"]["decision_relevance"] = "DECISIVE"
    assert schedule([a, b])["selected"][0] == "B"


def test_scheduler_blocks_invalid_contract_before_governor():
    t = base_task("BAD")
    t.pop("proposed_action")
    out = schedule([t])
    assert out["selected"] == []
    assert out["blocked"][0]["decision"] == "BLOCK_INVALID_CONTRACT"


def test_scheduler_blocks_non_ready_state():
    t = base_task("BLOCKED")
    t["state"] = "BLOCKED"
    out = schedule([t])
    assert out["selected"] == []
    assert out["blocked"][0]["decision"] == "BLOCK_NON_READY_STATE"


def test_scheduler_waiting_state_is_not_selected():
    t = base_task("WAIT")
    t["state"] = "WAITING_FOR_DATA"
    out = schedule([t])
    assert out["selected"] == []
    assert out["waiting"][0]["task_id"] == "WAIT"


def test_scheduler_governor_blocks_missing_provenance():
    t = base_task("NOPROV")
    t["proposed_action"]["provenance"] = False
    out = schedule([t])
    assert out["selected"] == []
    assert out["blocked"][0]["decision"] == "BLOCK"


def test_shadow_cycle_never_mutates_or_promotes():
    candidate = {"candidate_id": "C1", "hypothesis": "h", "decision": "UNPROVEN", "gates": {}}
    out = build_shadow_plan([candidate], [base_task()], source_commit="deadbeef")
    assert out["mode"] == "SHADOW_READ_ONLY"
    assert out["runtime_mutation"] is False
    assert out["live_trading"] is False
    assert out["economic_conclusion"] == "NO_PROVEN_EDGE"
    assert out["scheduled"]["selected"] == ["T1"]
    assert out["scheduled"]["tasks"][0]["fanout_cap"] == 5


def test_legacy_settlement_becomes_sequential_mechanics():
    task = packet_to_task({
        "agent_id": "settlement",
        "status": "READY",
        "input_refs": ["knowledge/routing.json"],
        "next_decisive_question": "Are settlement rules identical?",
    }, "R1")
    assert task["worker_domain"] == "mechanics"
    assert task["task_shape"]["dependency_shape"] == "SEQUENTIAL"
    assert task["state"] == "READY"
    assert task["constraints"]["live_trading"] is False
    assert validate_task(task) == []


def test_legacy_unknown_status_fails_closed():
    task = packet_to_task({
        "agent_id": "settlement",
        "status": "MYSTERY_NEW_STATE",
        "input_refs": ["x"],
    }, "R")
    assert task["state"] == "BLOCKED"
    out = schedule([task])
    assert out["selected"] == []
    assert out["blocked"][0]["decision"] == "BLOCK_NON_READY_STATE"


def test_legacy_pending_does_not_become_ready():
    task = packet_to_task({
        "agent_id": "scout",
        "status": "PENDING",
        "input_refs": ["x"],
    }, "R")
    assert task["state"] == "BLOCKED"


def test_legacy_terminal_packet_does_not_create_task():
    assert packet_to_task({"agent_id": "scout", "status": "CLOSED_NEGATIVE"}, "R") is None
    assert packet_to_task({"agent_id": "scout", "status": "COMPLETED"}, "R") is None


def test_falsifier_and_reproducer_are_blinded():
    f = packet_to_task({"agent_id": "chief_falsifier", "status": "READY", "candidate_ids": ["C1"]}, "R")
    r = packet_to_task({"agent_id": "independent_reproducer", "status": "READY", "candidate_ids": ["C1"]}, "R")
    assert f["constraints"]["blind_to_origin_reasoning"] is True
    assert r["constraints"]["blind_to_origin_reasoning"] is True


def test_shadow_cli_reads_current_shapes_without_writes(tmp_path):
    cdir = tmp_path / "candidates"
    pdir = tmp_path / "packets" / "RUN1"
    cdir.mkdir()
    pdir.mkdir(parents=True)
    (cdir / "c.json").write_text(json.dumps({
        "candidate_id": "C1",
        "hypothesis": "h",
        "decision": "UNPROVEN",
        "gates": {},
    }))
    (pdir / "settlement.json").write_text(json.dumps({
        "agent_id": "settlement",
        "status": "READY",
        "input_refs": ["x"],
    }))
    out = build_from_paths(cdir, pdir, "abc")
    assert out["mode"] == "SHADOW_READ_ONLY"
    assert out["input_summary"]["candidate_count"] == 1
    assert out["input_summary"]["packet_count"] == 1
    assert out["scheduled"]["selected"] == ["RUN1:settlement"]


def test_adaptive_search_requires_untouched_validation():
    flags = adaptive_search_flags({
        "id": "F1",
        "hypotheses_examined": 4,
        "parameterizations_examined": 3,
        "post_hoc_mutations": 1,
        "untouched_evidence_remaining": True,
    })
    assert flags["adaptive_search"] is True
    assert flags["requires_untouched_validation"] is True
    assert flags["discovery_evidence_may_promote_directly"] is False


def test_discovery_coverage_measures_overlap_and_gaps():
    p = [{
        "source_id": "a",
        "document_sha256": "1",
        "source_family": "OFFICIAL",
        "source_authority": "OFFICIAL_PRIMARY",
        "relevant": True,
    }]
    r = [{
        "source_id": "a",
        "document_sha256": "1",
        "source_family": "COMMUNITY",
        "source_class": "COMMUNITY",
        "relevant": True,
    }]
    out = summarize_coverage(p, r, ["OFFICIAL"], ["OFFICIAL", "CODE"])
    assert out["duplicate_cross_scout_keys"] == 1
    assert out["coverage_gaps"] == ["CODE"]
    assert out["raw_item_count_is_success_metric"] is False


def test_promotion_cannot_override_failed_gate_or_authorize_trading():
    candidate = promotion_candidate()
    candidate["required_gates"]["execution_reality"] = "FAIL"
    out = evaluate_promotion(candidate)
    assert out["eligible"] is False
    assert out["director_override_allowed"] is False
    assert out["live_trading_authorized"] is False


def test_promotion_candidate_still_does_not_authorize_live():
    out = evaluate_promotion(promotion_candidate())
    assert out["status"] == "PROMOTION_CANDIDATE"
    assert out["live_trading_authorized"] is False


def test_no_signal_route_requires_explicit_not_applicable():
    unknown = evaluate_promotion(promotion_candidate("PENDING"), signal_required=False)
    assert unknown["eligible"] is False
    assert "signal_edge_not_explicitly_not_applicable" in unknown["block_reasons"]
    explicit = evaluate_promotion(promotion_candidate("NOT_APPLICABLE"), signal_required=False)
    assert explicit["status"] == "PROMOTION_CANDIDATE"
    assert explicit["live_trading_authorized"] is False


def test_resurrection_requires_stored_changed_condition_and_resets_validation():
    c = {
        "candidate_id": "C",
        "queue_status": "CLOSED_NEGATIVE",
        "economic_status": "TESTED_NEGATIVE",
        "phase": "VALIDATION",
        "resurrection_conditions": ["reward_active"],
        "required_gates": {
            "source_provenance": "PASS",
            "mechanism": "PASS",
            "execution_reality": "PASS",
        },
    }
    out = evaluate_resurrection(c, ["reward_active"], "2026-09-21T00:00:00Z")
    assert out["resurrected"] is True
    assert out["old_validation_inherited"] is False
    assert out["old_gate_passes_inherited"] is False
    assert out["candidate"]["required_gates"]["execution_reality"] == "PENDING"
    assert out["candidate"]["required_gates"]["source_provenance"] == "PENDING"
    assert out["candidate"]["resurrection_history"][0]["required_gates"]["mechanism"] == "PASS"


def test_red_team_packet_excludes_origin_reasoning():
    p = build_blind_packet({
        "candidate_id": "C",
        "hypothesis": "h",
        "supporting_evidence": ["e1"],
        "required_gates": {},
    })
    assert p["origin_reasoning_included"] is False
    assert p["economic_promotion_authority"] is False
    assert p["attack_order"][0] == "SEMANTIC_SOURCE"


def test_reproduction_with_shared_reference_is_not_independent():
    out = source_independence(["raw:a", "derived:b"], ["derived:b", "new:c"])
    assert out["counts_as_independent_reproduction"] is False
    assert out["status"] == "SHARED_UPSTREAM"


def test_reproduction_disjoint_refs_without_lineage_remain_unknown():
    out = source_independence(["derived:a"], ["derived:b"])
    assert out["status"] == "UNKNOWN"
    assert out["independence_proof_complete"] is False
    assert out["counts_as_independent_reproduction"] is False


def test_reproduction_explicit_disjoint_upstream_can_be_independent():
    origin = [{"ref": "derived:a", "upstream_source_ids": ["official:source-a"]}]
    repro = [{"ref": "derived:b", "upstream_source_ids": ["official:source-b"]}]
    out = source_independence(origin, repro)
    assert out["status"] == "INDEPENDENT"
    assert out["independence_proof_complete"] is True
    assert out["counts_as_independent_reproduction"] is True


def test_shadow_benchmark_has_no_composite_score_and_no_auto_activation():
    b = summarize_benchmark(benchmark_rows())
    c = summarize_benchmark(benchmark_rows(better=True))
    verdict = replacement_check(b, c)
    assert verdict["comparable_case_set"] is True
    assert verdict["strict_improvement_count"] >= 2
    assert verdict["scientific_replacement_gate_met"] is True
    assert verdict["automatic_runtime_replacement_authorized"] is False


def test_shadow_benchmark_missing_denominators_fail_closed():
    rows = benchmark_rows()
    for row in rows:
        row["worker_runs"] = 0
        row["research_items"] = 0
    summary = summarize_benchmark(rows)
    assert summary["M1_unique_relevant_evidence_per_worker_run"] is None
    assert summary["M2_duplicate_research_ratio"] is None
    verdict = replacement_check(summary, summarize_benchmark(benchmark_rows(better=True)))
    assert verdict["scientific_replacement_gate_met"] is False


def test_shadow_benchmark_requires_identical_case_set():
    baseline = summarize_benchmark(benchmark_rows())
    challenger = summarize_benchmark(benchmark_rows(better=True, case_prefix="OTHER"))
    verdict = replacement_check(baseline, challenger)
    assert verdict["comparable_case_set"] is False
    assert verdict["scientific_replacement_gate_met"] is False


def test_shadow_benchmark_missing_case_ids_fail_closed():
    rows = benchmark_rows()
    rows[0].pop("case_id")
    summary = summarize_benchmark(rows)
    assert "missing_case_id" in summary["validation_errors"]
    assert summary["case_id_complete"] is False
