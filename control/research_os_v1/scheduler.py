from __future__ import annotations

from typing import Any

from .governor import classify
from .policy import load_task_shape_policy

LEVEL = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "DECISIVE": 3}
NOVELTY = {"DUPLICATE": 0, "INCREMENTAL": 1, "NOVEL": 2}
UNLOCK = {"NONE": 0, "ONE": 1, "MULTIPLE": 2}
COST = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}


def fanout_cap(task: dict[str, Any], shape_policy: dict[str, Any] | None = None) -> int:
    shape_policy = shape_policy or load_task_shape_policy()
    shape = task.get("task_shape") or {}
    dep = str(shape.get("dependency_shape") or "")
    par = str(shape.get("parallelism") or "")
    key = "LOW_SEQUENTIAL" if dep == "SEQUENTIAL" or par == "LOW" else (
        "HIGH_INDEPENDENT" if dep == "INDEPENDENT" and par == "HIGH" else "MEDIUM_PARTIAL"
    )
    return int(shape_policy["fanout"][key]["max_specialist_workers"])


def _rank(task: dict[str, Any]) -> tuple:
    """Lower tuple sorts first. Implements ordinal policy, not fake decimal EV."""
    shape = task.get("task_shape") or {}
    sched = task.get("scheduling") or {}
    decision = LEVEL.get(str(shape.get("decision_relevance") or "LOW"), 0)
    uncertainty = LEVEL.get(str(sched.get("uncertainty_reduction") or "LOW"), 0)
    unlock = UNLOCK.get(str(sched.get("dependency_unlock_value") or "NONE"), 0)
    time = LEVEL.get(str(shape.get("time_sensitivity") or "LOW"), 0)
    novelty = NOVELTY.get(str(shape.get("novelty") or "DUPLICATE"), 0)
    evidence_cost = COST.get(str(sched.get("evidence_cost") or "HIGH"), 2)
    model_cost = COST.get(str(sched.get("model_cost") or "HIGH"), 2)
    duplication = COST.get(str(sched.get("duplication_risk") or "HIGH"), 2)
    return (-decision, -uncertainty, -unlock, -time, -novelty, evidence_cost, model_cost, duplication, str(task.get("task_id") or ""))


def schedule(tasks: list[dict[str, Any]], max_tasks: int | None = None) -> dict[str, Any]:
    runnable, blocked, waiting = [], [], []
    for task in tasks:
        if str(task.get("state") or "READY") in {"WAITING_FOR_DATA", "WAITING_FOR_RESULT", "PARKED"}:
            waiting.append({"task_id": task.get("task_id"), "reason": "non_runnable_state"})
            continue
        action = task.get("proposed_action") or {
            "kind": "free_public_read_only_research",
            "provenance": True,
            "point_in_time": True,
        }
        decision = classify(action)
        if not decision.admissible:
            blocked.append({"task_id": task.get("task_id"), "decision": decision.decision, "reason": decision.reason})
            continue
        runnable.append(task)

    runnable.sort(key=_rank)
    if max_tasks is not None:
        runnable = runnable[:max_tasks]
    return {
        "selected": [t.get("task_id") for t in runnable],
        "tasks": runnable,
        "blocked": blocked,
        "waiting": waiting,
        "economic_conclusion": "NO_PROVEN_EDGE",
    }
