from __future__ import annotations

from typing import Any

from .contracts import validate_task
from .governor import classify
from .policy import load_task_shape_policy

LEVEL = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "DECISIVE": 3}
NOVELTY = {"DUPLICATE": 0, "INCREMENTAL": 1, "NOVEL": 2}
UNLOCK = {"NONE": 0, "ONE": 1, "MULTIPLE": 2}
COST = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
WAITING_STATES = {"WAITING_FOR_DATA", "WAITING_FOR_RESULT", "PARKED"}


def fanout_cap(task: dict[str, Any], shape_policy: dict[str, Any] | None = None) -> int:
    errors = validate_task(task)
    if errors:
        raise ValueError("invalid_task_contract:" + ",".join(errors))

    if shape_policy is None:
        shape_policy = load_task_shape_policy()
    if not isinstance(shape_policy, dict):
        raise ValueError("shape_policy_must_be_object")

    shape = task["task_shape"]
    dep = shape["dependency_shape"]
    par = shape["parallelism"]
    key = "LOW_SEQUENTIAL" if dep == "SEQUENTIAL" or par == "LOW" else (
        "HIGH_INDEPENDENT" if dep == "INDEPENDENT" and par == "HIGH" else "MEDIUM_PARTIAL"
    )

    try:
        value = shape_policy["fanout"][key]["max_specialist_workers"]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"fanout_policy_missing:{key}") from exc
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"fanout_policy_invalid:{key}")
    return value


def _rank(task: dict[str, Any]) -> tuple:
    """Lower tuple sorts first. Implements ordinal policy, not fake decimal EV."""
    shape = task["task_shape"]
    sched = task["scheduling"]
    decision = LEVEL[shape["decision_relevance"]]
    uncertainty = LEVEL[sched["uncertainty_reduction"]]
    unlock = UNLOCK[sched["dependency_unlock_value"]]
    time = LEVEL[shape["time_sensitivity"]]
    novelty = NOVELTY[shape["novelty"]]
    evidence_cost = COST[sched["evidence_cost"]]
    model_cost = COST[sched["model_cost"]]
    duplication = COST[sched["duplication_risk"]]
    return (
        -decision,
        -uncertainty,
        -unlock,
        -time,
        -novelty,
        evidence_cost,
        model_cost,
        duplication,
        task["task_id"],
    )


def schedule(tasks: list[dict[str, Any]], max_tasks: int | None = None) -> dict[str, Any]:
    if not isinstance(tasks, list):
        raise ValueError("tasks_must_be_list")
    if max_tasks is not None and (
        not isinstance(max_tasks, int)
        or isinstance(max_tasks, bool)
        or max_tasks < 0
    ):
        raise ValueError("max_tasks_must_be_non_negative_integer_or_none")

    runnable: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    waiting: list[dict[str, Any]] = []

    for task in tasks:
        contract_errors = validate_task(task)
        if contract_errors:
            blocked.append({
                "task_id": task.get("task_id") if isinstance(task, dict) else None,
                "decision": "BLOCK_INVALID_CONTRACT",
                "reason": "invalid_contract",
                "contract_errors": contract_errors,
            })
            continue

        state = task["state"]
        if state in WAITING_STATES:
            waiting.append({
                "task_id": task["task_id"],
                "reason": f"non_runnable_state:{state}",
            })
            continue
        if state != "READY":
            blocked.append({
                "task_id": task["task_id"],
                "decision": "BLOCK_NON_READY_STATE",
                "reason": f"non_runnable_state:{state}",
            })
            continue

        decision = classify(task["proposed_action"])
        if not decision.admissible:
            blocked.append({
                "task_id": task["task_id"],
                "decision": decision.decision,
                "reason": decision.reason,
            })
            continue

        runnable.append(task)

    runnable.sort(key=_rank)
    if max_tasks is not None:
        runnable = runnable[:max_tasks]

    return {
        "selected": [t["task_id"] for t in runnable],
        "tasks": runnable,
        "blocked": blocked,
        "waiting": waiting,
        "economic_conclusion": "NO_PROVEN_EDGE",
    }
