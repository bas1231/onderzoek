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


def _require(cond: bool, message: str, errors: list[str]) -> None:
    if not cond:
        errors.append(message)


def validate_task(task: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    _require(isinstance(task, dict), "task_must_be_object", errors)
    if not isinstance(task, dict):
        return errors

    _require(bool(str(task.get("task_id") or "").strip()), "task_id_required", errors)
    _require(task.get("worker_domain") in DOMAINS, "invalid_worker_domain", errors)
    _require(bool(str(task.get("objective") or "").strip()), "objective_required", errors)
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

    _require(isinstance(task.get("inputs"), dict), "inputs_required", errors)

    expected = task.get("expected_output") if isinstance(task.get("expected_output"), dict) else {}
    _require(expected.get("artifact_type") in ARTIFACT_TYPES, "invalid_artifact_type", errors)
    required_fields = expected.get("required_fields")
    _require(
        isinstance(required_fields, list)
        and bool(required_fields)
        and all(isinstance(v, str) and bool(v.strip()) for v in required_fields),
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
    _require(bool(str(action.get("kind") or "").strip()), "proposed_action_kind_required", errors)
    _require(isinstance(action.get("provenance"), bool), "proposed_action_provenance_bool_required", errors)
    _require(isinstance(action.get("point_in_time"), bool), "proposed_action_point_in_time_bool_required", errors)

    return sorted(set(errors))


def validate_result(result: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    _require(isinstance(result, dict), "result_must_be_object", errors)
    if not isinstance(result, dict):
        return errors
    _require(result.get("status") in RESULT_STATUS, "invalid_result_status", errors)
    for key in ("claims", "evidence", "contradictions", "unknowns", "gate_effect"):
        _require(isinstance(result.get(key), list), f"{key}_must_be_list", errors)
    _require(result.get("economic_conclusion") in ECONOMIC, "invalid_economic_conclusion", errors)
    return sorted(set(errors))
