from __future__ import annotations

from typing import Any

DOMAINS = {
    "discovery", "market_research", "mechanics", "algebra",
    "red_team", "research_director", "independent_reproducer",
}
PARALLELISM = {"LOW", "MEDIUM", "HIGH"}
DEPENDENCY = {"INDEPENDENT", "PARTIAL", "SEQUENTIAL"}
UNCERTAINTY = {"SOURCE", "SEMANTIC", "MECHANISM", "SIGNAL", "MARKET", "EXECUTION", "ROBUSTNESS", "PROCESS"}
DECISION_RELEVANCE = {"LOW", "MEDIUM", "HIGH", "DECISIVE"}
TIME_SENSITIVITY = {"LOW", "MEDIUM", "HIGH"}
NOVELTY = {"DUPLICATE", "INCREMENTAL", "NOVEL"}
TASK_STATES = {"READY", "WAITING_FOR_DATA", "WAITING_FOR_RESULT", "PARKED", "BLOCKED"}
SOURCE_POLICIES = {"FREE_PUBLIC_ONLY", "LOCAL_EXISTING_ONLY"}
ARTIFACT_TYPES = {"DISCOVERY_FINDING", "RESEARCH_FINDING", "FALSIFICATION", "REPRODUCTION", "DIRECTOR_DECISION"}
UNCERTAINTY_REDUCTION = {"LOW", "MEDIUM", "HIGH", "DECISIVE"}
DEPENDENCY_UNLOCK = {"NONE", "ONE", "MULTIPLE"}
COST_LEVEL = {"LOW", "MEDIUM", "HIGH"}
RESULT_STATUS = {"COMPLETE", "BLOCKED", "FAILED", "NO_NEW_EVIDENCE"}
ECONOMIC = {"NO_PROVEN_EDGE", "RESEARCH_POSITIVE", "TESTED_NEGATIVE", "EXECUTION_BLOCKED", "STRUCTURAL_CANDIDATE"}
SOURCE_INDEPENDENCE = {"UNKNOWN", "SHARED_UPSTREAM", "PARTIAL", "INDEPENDENT", "NOT_APPLICABLE"}
GATE_STATES = {"PASS", "FAIL", "PENDING", "UNKNOWN", "NOT_APPLICABLE"}
POSITIVE_ECONOMIC = {"RESEARCH_POSITIVE", "STRUCTURAL_CANDIDATE"}


def _require(cond: bool, message: str, errors: list[str]) -> None:
    if not cond:
        errors.append(message)


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _optional_nonempty_string(value: Any) -> bool:
    return value is None or _nonempty_string(value)


def _string_list(value: Any, *, nonempty: bool = False) -> bool:
    return (
        isinstance(value, list)
        and (bool(value) if nonempty else True)
        and all(_nonempty_string(item) for item in value)
    )


def validate_task(task: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    _require(isinstance(task, dict), "task_must_be_object", errors)
    if not isinstance(task, dict):
        return errors

    _require(_nonempty_string(task.get("task_id")), "task_id_required", errors)
    _require(
        _optional_nonempty_string(task.get("candidate_id")),
        "candidate_id_must_be_string_or_null",
        errors,
    )
    for key in ("legacy_role", "legacy_status"):
        if key in task:
            _require(
                _optional_nonempty_string(task.get(key)),
                f"{key}_must_be_string_or_null",
                errors,
            )
    _require(task.get("worker_domain") in DOMAINS, "invalid_worker_domain", errors)
    _require(_nonempty_string(task.get("objective")), "objective_required", errors)
    _require(
        _optional_nonempty_string(task.get("decisive_question")),
        "decisive_question_must_be_string_or_null",
        errors,
    )
    _require(task.get("state") in TASK_STATES, "invalid_task_state", errors)

    shape = task.get("task_shape") if isinstance(task.get("task_shape"), dict) else {}
    _require(shape.get("parallelism") in PARALLELISM, "invalid_parallelism", errors)
    _require(shape.get("dependency_shape") in DEPENDENCY, "invalid_dependency_shape", errors)
    _require(shape.get("uncertainty_type") in UNCERTAINTY, "invalid_uncertainty_type", errors)
    _require(shape.get("time_sensitivity") in TIME_SENSITIVITY, "invalid_time_sensitivity", errors)
    _require(shape.get("novelty") in NOVELTY, "invalid_novelty", errors)
    _require(shape.get("decision_relevance") in DECISION_RELEVANCE, "invalid_decision_relevance", errors)

    constraints = task.get("constraints") if isinstance(task.get("constraints"), dict) else {}
    for key in ("live_trading", "paid_actions", "wallet_actions"):
        _require(constraints.get(key) is False, f"{key}_must_be_false", errors)
    _require(constraints.get("source_policy") in SOURCE_POLICIES, "invalid_source_policy", errors)
    blind = constraints.get("blind_to_origin_reasoning")
    _require(
        blind is None or isinstance(blind, bool),
        "blind_to_origin_reasoning_must_be_boolean_or_absent",
        errors,
    )

    inputs = task.get("inputs") if isinstance(task.get("inputs"), dict) else None
    _require(inputs is not None, "inputs_required", errors)
    if inputs is not None:
        for key in (
            "claim_ids", "evidence_refs", "rule_refs", "negative_evidence_refs",
            "failure_pattern_ids", "candidate_ids",
        ):
            if key in inputs:
                _require(
                    _string_list(inputs.get(key)),
                    f"invalid_input_{key}",
                    errors,
                )
        if "routed_evidence_count" in inputs:
            count = inputs.get("routed_evidence_count")
            _require(
                isinstance(count, int) and not isinstance(count, bool) and count >= 0,
                "invalid_routed_evidence_count",
                errors,
            )
        if "point_in_time_cutoff" in inputs:
            _require(
                _optional_nonempty_string(inputs.get("point_in_time_cutoff")),
                "invalid_point_in_time_cutoff",
                errors,
            )

    expected = task.get("expected_output") if isinstance(task.get("expected_output"), dict) else {}
    _require(expected.get("artifact_type") in ARTIFACT_TYPES, "invalid_artifact_type", errors)
    _require(
        _string_list(expected.get("required_fields"), nonempty=True),
        "invalid_required_fields",
        errors,
    )

    scheduling = task.get("scheduling") if isinstance(task.get("scheduling"), dict) else {}
    _require(scheduling.get("uncertainty_reduction") in UNCERTAINTY_REDUCTION, "invalid_uncertainty_reduction", errors)
    _require(scheduling.get("dependency_unlock_value") in DEPENDENCY_UNLOCK, "invalid_dependency_unlock_value", errors)
    _require(scheduling.get("evidence_cost") in COST_LEVEL, "invalid_evidence_cost", errors)
    _require(scheduling.get("model_cost") in COST_LEVEL, "invalid_model_cost", errors)
    _require(scheduling.get("duplication_risk") in COST_LEVEL, "invalid_duplication_risk", errors)

    action = task.get("proposed_action") if isinstance(task.get("proposed_action"), dict) else {}
    _require(_nonempty_string(action.get("kind")), "proposed_action_kind_required", errors)
    _require(isinstance(action.get("provenance"), bool), "proposed_action_provenance_bool_required", errors)
    _require(isinstance(action.get("point_in_time"), bool), "proposed_action_point_in_time_bool_required", errors)
    if "branch" in action:
        _require(
            _optional_nonempty_string(action.get("branch")),
            "proposed_action_branch_must_be_string_or_null",
            errors,
        )
    if "contains_secrets" in action:
        _require(
            isinstance(action.get("contains_secrets"), bool),
            "proposed_action_contains_secrets_bool_required",
            errors,
        )

    if "stop_conditions" in task:
        _require(
            _string_list(task.get("stop_conditions")),
            "invalid_stop_conditions",
            errors,
        )

    return sorted(set(errors))


def validate_result(result: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    _require(isinstance(result, dict), "result_must_be_object", errors)
    if not isinstance(result, dict):
        return errors

    _require(result.get("status") in RESULT_STATUS, "invalid_result_status", errors)
    for key in ("claims", "evidence", "contradictions", "gate_effect"):
        value = result.get(key)
        _require(
            isinstance(value, list) and all(isinstance(item, dict) for item in value),
            f"{key}_must_be_list_of_objects",
            errors,
        )
    _require(
        _string_list(result.get("unknowns")),
        "unknowns_must_be_string_list",
        errors,
    )
    if "failure_patterns_triggered" in result:
        _require(
            _string_list(result.get("failure_patterns_triggered")),
            "failure_patterns_triggered_must_be_string_list",
            errors,
        )
    if "next_decisive_test" in result:
        _require(
            _optional_nonempty_string(result.get("next_decisive_test")),
            "next_decisive_test_must_be_string_or_null",
            errors,
        )
    if "source_independence" in result:
        _require(
            result.get("source_independence") in SOURCE_INDEPENDENCE,
            "invalid_source_independence",
            errors,
        )
    _require(result.get("economic_conclusion") in ECONOMIC, "invalid_economic_conclusion", errors)
    return sorted(set(errors))


def _provenance_object(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    ref = item.get("source_ref") or item.get("evidence_ref") or item.get("ref")
    content_hash = item.get("content_hash") or item.get("document_sha256")
    if not (_nonempty_string(ref) or _nonempty_string(content_hash)):
        return False
    return item.get("point_in_time_status") in GATE_STATES


def _reference_ids(item: Any) -> set[str]:
    if not isinstance(item, dict):
        return set()
    out: set[str] = set()
    for key in ("source_ref", "evidence_ref", "ref"):
        value = item.get(key)
        if _nonempty_string(value):
            out.add(value.strip())
    for key in ("content_hash", "document_sha256"):
        value = item.get(key)
        if _nonempty_string(value):
            clean = value.strip()
            out.add(clean)
            out.add(f"sha256:{clean.lower()}")
    return out


def _known_basis_refs(task: dict[str, Any], result: dict[str, Any]) -> set[str]:
    known: set[str] = set()
    inputs = task.get("inputs") if isinstance(task.get("inputs"), dict) else {}
    for key in ("evidence_refs", "rule_refs", "negative_evidence_refs"):
        values = inputs.get(key) or []
        if isinstance(values, list):
            known.update(v.strip() for v in values if _nonempty_string(v))
    for key in ("evidence", "contradictions"):
        for item in result.get(key) or []:
            known.update(_reference_ids(item))
    return known


def validate_result_for_task(task: dict[str, Any], result: dict[str, Any]) -> list[str]:
    """Validate a worker result in the authority/context of its originating task."""
    errors = list(validate_task(task))
    errors.extend(validate_result(result))
    if errors:
        return sorted(set(errors))

    task_id = task["task_id"]
    domain = task["worker_domain"]
    candidate_id = task.get("candidate_id")

    _require(result.get("task_id") == task_id, "result_task_id_mismatch", errors)
    _require(result.get("worker_domain") == domain, "result_worker_domain_mismatch", errors)
    if candidate_id is not None:
        _require(
            result.get("candidate_id") == candidate_id,
            "result_candidate_id_mismatch",
            errors,
        )

    status = result["status"]
    economic = result["economic_conclusion"]

    if status == "FAILED":
        _require(economic == "NO_PROVEN_EDGE", "failed_result_may_not_set_economic_state", errors)
    elif status == "NO_NEW_EVIDENCE":
        _require(economic == "NO_PROVEN_EDGE", "no_new_evidence_may_not_set_economic_state", errors)
    elif status == "BLOCKED":
        _require(
            economic in {"NO_PROVEN_EDGE", "EXECUTION_BLOCKED"},
            "blocked_result_has_invalid_economic_state",
            errors,
        )

    if domain in {"discovery", "red_team"}:
        _require(
            economic not in POSITIVE_ECONOMIC,
            f"{domain}_may_not_emit_positive_economic_conclusion",
            errors,
        )

    if result.get("source_independence") == "INDEPENDENT":
        _require(
            domain == "independent_reproducer",
            "only_independent_reproducer_may_assert_source_independence",
            errors,
        )
    if domain == "independent_reproducer" and status == "COMPLETE":
        _require(
            result.get("source_independence") in SOURCE_INDEPENDENCE,
            "reproducer_complete_requires_source_independence_state",
            errors,
        )

    for index, item in enumerate(result.get("evidence") or []):
        _require(
            _provenance_object(item),
            f"evidence_missing_provenance:{index}",
            errors,
        )
    for index, item in enumerate(result.get("contradictions") or []):
        _require(
            _provenance_object(item),
            f"contradiction_missing_provenance:{index}",
            errors,
        )

    known_basis_refs = _known_basis_refs(task, result)
    seen_gate_effects: set[str] = set()
    for index, effect in enumerate(result.get("gate_effect") or []):
        gate = effect.get("gate") if isinstance(effect, dict) else None
        state = effect.get("state") if isinstance(effect, dict) else None
        _require(_nonempty_string(gate), f"gate_effect_gate_required:{index}", errors)
        _require(state in GATE_STATES, f"invalid_gate_effect_state:{index}", errors)
        if _nonempty_string(gate):
            normalized_gate = gate.strip()
            _require(
                normalized_gate not in seen_gate_effects,
                f"duplicate_gate_effect:{normalized_gate}",
                errors,
            )
            seen_gate_effects.add(normalized_gate)
        basis_refs = effect.get("basis_refs") if isinstance(effect, dict) else None
        if state in {"PASS", "FAIL"}:
            _require(
                _string_list(basis_refs, nonempty=True),
                f"gate_effect_basis_required:{index}",
                errors,
            )
        elif basis_refs is not None:
            _require(
                _string_list(basis_refs),
                f"gate_effect_basis_invalid:{index}",
                errors,
            )
        if _string_list(basis_refs) if basis_refs is not None else False:
            for basis_ref in basis_refs:
                _require(
                    basis_ref.strip() in known_basis_refs,
                    f"gate_effect_unknown_basis_ref:{index}:{basis_ref.strip()}",
                    errors,
                )

    return sorted(set(errors))
