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
RESULT_STATUS = {"COMPLETE", "BLOCKED", "FAILED", "NO_NEW_EVIDENCE"}
ECONOMIC = {"NO_PROVEN_EDGE", "RESEARCH_POSITIVE", "TESTED_NEGATIVE", "EXECUTION_BLOCKED", "STRUCTURAL_CANDIDATE"}


def _require(cond: bool, message: str, errors: list[str]) -> None:
    if not cond:
        errors.append(message)


def validate_task(task: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    _require(bool(task.get("task_id")), "task_id_required", errors)
    _require(task.get("worker_domain") in DOMAINS, "invalid_worker_domain", errors)
    _require(bool(task.get("objective")), "objective_required", errors)
    shape = task.get("task_shape") if isinstance(task.get("task_shape"), dict) else {}
    _require(shape.get("parallelism") in PARALLELISM, "invalid_parallelism", errors)
    _require(shape.get("dependency_shape") in DEPENDENCY, "invalid_dependency_shape", errors)
    _require(shape.get("uncertainty_type") in UNCERTAINTY, "invalid_uncertainty_type", errors)
    _require(shape.get("decision_relevance") in DECISION_RELEVANCE, "invalid_decision_relevance", errors)
    constraints = task.get("constraints") if isinstance(task.get("constraints"), dict) else {}
    for key in ("live_trading", "paid_actions", "wallet_actions"):
        _require(constraints.get(key) is False, f"{key}_must_be_false", errors)
    _require(isinstance(task.get("inputs"), dict), "inputs_required", errors)
    _require(isinstance(task.get("expected_output"), dict), "expected_output_required", errors)
    return errors


def validate_result(result: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    _require(result.get("status") in RESULT_STATUS, "invalid_result_status", errors)
    for key in ("claims", "evidence", "contradictions", "unknowns", "gate_effect"):
        _require(isinstance(result.get(key), list), f"{key}_must_be_list", errors)
    _require(result.get("economic_conclusion") in ECONOMIC, "invalid_economic_conclusion", errors)
    return errors
