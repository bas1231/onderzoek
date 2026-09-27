from control.research_os_v1.contracts import validate_result_for_task


def task(domain="market_research", candidate_id="C1"):
    return {
        "task_id": "T1",
        "candidate_id": candidate_id,
        "worker_domain": domain,
        "objective": "validate result authority",
        "state": "READY",
        "task_shape": {
            "parallelism": "LOW",
            "dependency_shape": "SEQUENTIAL",
            "uncertainty_type": "MARKET",
            "time_sensitivity": "LOW",
            "novelty": "INCREMENTAL",
            "decision_relevance": "HIGH",
        },
        "inputs": {},
        "constraints": {
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
            "source_policy": "LOCAL_EXISTING_ONLY",
        },
        "expected_output": {
            "artifact_type": "RESEARCH_FINDING",
            "required_fields": ["evidence"],
        },
        "scheduling": {
            "uncertainty_reduction": "HIGH",
            "dependency_unlock_value": "ONE",
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


def result(domain="market_research", economic="NO_PROVEN_EDGE", status="COMPLETE"):
    return {
        "task_id": "T1",
        "candidate_id": "C1",
        "worker_domain": domain,
        "status": status,
        "claims": [],
        "evidence": [],
        "contradictions": [],
        "unknowns": [],
        "gate_effect": [],
        "economic_conclusion": economic,
    }


def evidence(ref="raw/e1.json", state="PASS"):
    return {
        "source_ref": ref,
        "point_in_time_status": state,
    }


def test_matching_complete_research_result_is_valid():
    assert validate_result_for_task(task(), result()) == []


def test_result_identity_must_match_task():
    bad = result()
    bad["task_id"] = "OTHER"
    errors = validate_result_for_task(task(), bad)
    assert "result_task_id_mismatch" in errors


def test_discovery_may_not_emit_positive_economic_conclusion():
    errors = validate_result_for_task(
        task(domain="discovery"),
        result(domain="discovery", economic="RESEARCH_POSITIVE"),
    )
    assert "discovery_may_not_emit_positive_economic_conclusion" in errors


def test_red_team_may_not_emit_structural_candidate():
    errors = validate_result_for_task(
        task(domain="red_team"),
        result(domain="red_team", economic="STRUCTURAL_CANDIDATE"),
    )
    assert "red_team_may_not_emit_positive_economic_conclusion" in errors


def test_failed_result_cannot_carry_positive_state():
    errors = validate_result_for_task(
        task(),
        result(economic="RESEARCH_POSITIVE", status="FAILED"),
    )
    assert "failed_result_may_not_set_economic_state" in errors


def test_no_new_evidence_cannot_carry_prior_positive_state_as_new_result():
    errors = validate_result_for_task(
        task(),
        result(economic="STRUCTURAL_CANDIDATE", status="NO_NEW_EVIDENCE"),
    )
    assert "no_new_evidence_may_not_set_economic_state" in errors


def test_evidence_requires_provenance_and_point_in_time_state():
    bad = result()
    bad["evidence"] = [{"statement": "looks useful"}]
    errors = validate_result_for_task(task(), bad)
    assert "evidence_missing_provenance:0" in errors


def test_contradiction_requires_provenance_too():
    bad = result()
    bad["contradictions"] = [{"source_ref": "raw/c1.json"}]
    errors = validate_result_for_task(task(), bad)
    assert "contradiction_missing_provenance:0" in errors


def test_gate_pass_requires_nonempty_basis_refs():
    bad = result()
    bad["gate_effect"] = [{"gate": "mechanism", "state": "PASS", "basis_refs": []}]
    errors = validate_result_for_task(task(), bad)
    assert "gate_effect_basis_required:0" in errors


def test_gate_pass_with_result_evidence_basis_is_valid():
    good = result()
    good["evidence"] = [evidence()]
    good["gate_effect"] = [{
        "gate": "mechanism",
        "state": "PASS",
        "basis_refs": ["raw/e1.json"],
    }]
    assert validate_result_for_task(task(), good) == []


def test_gate_pass_with_preregistered_task_input_basis_is_valid():
    t = task()
    t["inputs"]["rule_refs"] = ["rules/contract-v1.json"]
    good = result()
    good["gate_effect"] = [{
        "gate": "mechanism",
        "state": "PASS",
        "basis_refs": ["rules/contract-v1.json"],
    }]
    assert validate_result_for_task(t, good) == []


def test_gate_pass_with_invented_basis_ref_is_rejected():
    bad = result()
    bad["evidence"] = [evidence("raw/real.json")]
    bad["gate_effect"] = [{
        "gate": "mechanism",
        "state": "PASS",
        "basis_refs": ["raw/invented.json"],
    }]
    errors = validate_result_for_task(task(), bad)
    assert "gate_effect_unknown_basis_ref:0:raw/invented.json" in errors


def test_hash_basis_can_reference_evidence_hash_identity():
    good = result()
    good["evidence"] = [{
        "document_sha256": "ABCDEF",
        "point_in_time_status": "PASS",
    }]
    good["gate_effect"] = [{
        "gate": "mechanism",
        "state": "PASS",
        "basis_refs": ["sha256:abcdef"],
    }]
    assert validate_result_for_task(task(), good) == []


def test_duplicate_gate_effect_is_rejected():
    bad = result()
    bad["gate_effect"] = [
        {"gate": "mechanism", "state": "UNKNOWN"},
        {"gate": "mechanism", "state": "PENDING"},
    ]
    errors = validate_result_for_task(task(), bad)
    assert "duplicate_gate_effect:mechanism" in errors


def test_only_reproducer_can_assert_independent_source_state():
    bad = result()
    bad["source_independence"] = "INDEPENDENT"
    errors = validate_result_for_task(task(), bad)
    assert "only_independent_reproducer_may_assert_source_independence" in errors


def test_complete_reproducer_must_report_source_independence_state():
    repro_task = task(domain="independent_reproducer")
    repro_result = result(domain="independent_reproducer")
    errors = validate_result_for_task(repro_task, repro_result)
    assert "reproducer_complete_requires_source_independence_state" in errors


def test_complete_reproducer_with_independence_state_is_valid():
    repro_task = task(domain="independent_reproducer")
    repro_result = result(domain="independent_reproducer")
    repro_result["source_independence"] = "UNKNOWN"
    assert validate_result_for_task(repro_task, repro_result) == []
