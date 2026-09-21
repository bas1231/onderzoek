from __future__ import annotations

from copy import deepcopy
from typing import Any

from .candidate_view import canonicalize
from .contracts import validate_task
from .failure_memory import required_checks
from .scheduler import fanout_cap, schedule


def build_shadow_plan(
    legacy_candidates: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
    source_commit: str,
) -> dict[str, Any]:
    """Read-only Research OS sidecar decision.

    Inputs are copied; no repository/runtime mutation occurs.
    """
    candidates = [canonicalize(deepcopy(c), source_commit=source_commit) for c in legacy_candidates]

    task_errors: dict[str, list[str]] = {}
    enriched = []
    for raw in tasks:
        task = deepcopy(raw)
        errors = validate_task(task)
        if errors:
            task_errors[str(task.get("task_id") or "<missing>")] = errors
            continue
        fps = list((task.get("inputs") or {}).get("failure_pattern_ids") or [])
        task["required_failure_checks"] = required_checks(fps)
        task["fanout_cap"] = fanout_cap(task)
        enriched.append(task)

    plan = schedule(enriched)
    return {
        "schema_version": 1,
        "mode": "SHADOW_READ_ONLY",
        "source_commit": source_commit,
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
