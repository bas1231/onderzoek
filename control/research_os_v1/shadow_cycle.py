from __future__ import annotations

from copy import deepcopy
from typing import Any

from .candidate_view import canonicalize
from .contracts import validate_task
from .failure_memory import required_checks
from .scheduler import fanout_cap, schedule


def _required_text(value: Any, error: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(error)
    return value.strip()


def _assert_unique_candidate_ids(candidates: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            raise ValueError(f"candidate_must_be_object:{index}")
        cid = _required_text(
            candidate.get("candidate_id"),
            f"candidate_id_required:{index}",
        )
        if cid in seen:
            raise ValueError(f"duplicate_candidate_id:{cid}")
        seen.add(cid)


def _assert_unique_task_ids(tasks: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            continue
        raw = task.get("task_id")
        if raw is None:
            continue
        if not isinstance(raw, str) or not raw.strip():
            continue
        tid = raw.strip()
        if tid in seen:
            raise ValueError(f"duplicate_task_id:{tid}")
        seen.add(tid)


def build_shadow_plan(
    legacy_candidates: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
    source_commit: str,
) -> dict[str, Any]:
    """Read-only Research OS sidecar decision.

    Inputs are copied; no repository/runtime mutation occurs. Ambiguous identity
    is rejected rather than silently collapsing records. Invalid task contracts
    are reported and excluded, never auto-repaired into runnable work.
    """
    source = _required_text(source_commit, "source_commit_required")
    if not isinstance(legacy_candidates, list) or not isinstance(tasks, list):
        raise ValueError("shadow_inputs_must_be_lists")

    candidate_inputs = deepcopy(legacy_candidates)
    task_inputs = deepcopy(tasks)
    _assert_unique_candidate_ids(candidate_inputs)
    _assert_unique_task_ids(task_inputs)

    candidates = [
        canonicalize(c, source_commit=source)
        for c in candidate_inputs
    ]

    task_errors: dict[str, list[str]] = {}
    enriched = []
    for index, raw in enumerate(task_inputs):
        task = deepcopy(raw)
        errors = validate_task(task)
        if errors:
            if isinstance(task, dict) and isinstance(task.get("task_id"), str):
                label = task["task_id"].strip() or f"<invalid:{index}>"
            else:
                label = f"<invalid:{index}>"
            task_errors[label] = errors
            continue
        fps = task["inputs"].get("failure_pattern_ids") or []
        task["required_failure_checks"] = required_checks(fps)
        task["fanout_cap"] = fanout_cap(task)
        enriched.append(task)

    plan = schedule(enriched)
    return {
        "schema_version": 1,
        "mode": "SHADOW_READ_ONLY",
        "source_commit": source,
        "canonical_candidates": candidates,
        "scheduled": plan,
        "invalid_tasks": task_errors,
        "runtime_mutation": False,
        "main_mutation": False,
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "economic_conclusion": "NO_PROVEN_EDGE",
    }
