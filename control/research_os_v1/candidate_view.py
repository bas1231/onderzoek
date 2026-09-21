from __future__ import annotations

from copy import deepcopy
from typing import Any

DEFAULT_GATES = [
    "source_provenance", "point_in_time", "mechanism", "signal_edge",
    "market_edge", "execution_reality", "prebuild_killer",
    "chief_falsifier", "independent_reproduction", "validation",
    "holdout", "shadow",
]

NEGATIVE_DECISIONS = {
    "FALSIFIED",
    "TESTED_NEGATIVE",
    "CLOSED_NEGATIVE",
}

NON_PROVEN_POSITIVE_DECISIONS = {
    "RESEARCH_POSITIVE": "RESEARCH_POSITIVE",
    "STRUCTURAL_CANDIDATE": "STRUCTURAL_CANDIDATE",
}

PRESERVABLE_ECONOMIC_STATES = {
    "NO_PROVEN_EDGE",
    "RESEARCH_POSITIVE",
    "STRUCTURAL_CANDIDATE",
    "EXECUTION_BLOCKED",
    "TESTED_NEGATIVE",
}


def _gate_status(value: Any) -> str:
    text = str(value or "PENDING").upper()
    if text == "PASS":
        return "PASS"
    if text in {"FAIL", "FAILED", "FALSIFIED", "NEGATIVE"}:
        return "FAIL"
    if text in {"N/A", "NA", "NOT_APPLICABLE"}:
        return "NOT_APPLICABLE"
    if text in {"UNKNOWN", "UNPROVEN"}:
        return "UNKNOWN"
    return "PENDING"


def _merged_gates(src: dict[str, Any]) -> dict[str, Any]:
    """Merge canonical and legacy gate maps without losing explicit state.

    Canonical `required_gates` is the base representation. A legacy `gates` map
    may add/override individual entries, but an empty legacy map may not erase a
    populated canonical map.
    """
    merged: dict[str, Any] = {}
    canonical = src.get("required_gates")
    legacy = src.get("gates")
    if isinstance(canonical, dict):
        merged.update(canonical)
    if isinstance(legacy, dict):
        merged.update(legacy)
    return merged


def _economic_status(src: dict[str, Any]) -> str:
    """Return the most conservative supported non-live economic state.

    Explicit negative/blocked state outranks optimistic stale metadata. Unknown
    or unsupported positive states are deliberately downgraded to
    `NO_PROVEN_EDGE`.
    """
    decision = str(src.get("decision") or "").upper()
    queue_status = str(src.get("queue_status") or "NEEDS_DIRECTOR").upper()
    raw = str(src.get("economic_status") or "").upper()

    if queue_status == "CLOSED_NEGATIVE" or decision in NEGATIVE_DECISIONS or raw == "TESTED_NEGATIVE":
        return "TESTED_NEGATIVE"
    if decision == "EXECUTION_BLOCKED" or raw == "EXECUTION_BLOCKED":
        return "EXECUTION_BLOCKED"
    if decision in NON_PROVEN_POSITIVE_DECISIONS:
        return NON_PROVEN_POSITIVE_DECISIONS[decision]
    if raw in PRESERVABLE_ECONOMIC_STATES:
        return raw
    return "NO_PROVEN_EDGE"


def canonicalize(candidate: dict[str, Any], source_commit: str, version: int = 1) -> dict[str, Any]:
    """Create a read-only canonical candidate view from legacy or canonical state.

    The projection is conservative and idempotent: explicit negative/blocking
    state cannot be overwritten by optimistic stale metadata, and projecting an
    already-canonical record preserves its scientific meaning.
    """
    src = deepcopy(candidate)
    cid = str(src.get("candidate_id") or "").strip()
    if not cid:
        raise ValueError("candidate_id_required")
    if not source_commit:
        raise ValueError("source_commit_required")

    raw_gates = _merged_gates(src)
    gates = {name: _gate_status(raw_gates.get(name)) for name in DEFAULT_GATES}
    for name, value in raw_gates.items():
        gates.setdefault(str(name), _gate_status(value))

    search = src.get("search_family")
    if search is not None and not isinstance(search, dict):
        search = None

    return {
        "candidate_id": cid,
        "version": int(version),
        "hypothesis": str(src.get("hypothesis") or ""),
        "mechanism": src.get("mechanism"),
        "phase": str(src.get("phase") or "DISCOVERED"),
        "queue_status": str(src.get("queue_status") or "NEEDS_DIRECTOR"),
        "economic_status": _economic_status(src),
        "priority": str(src.get("priority") or "P3"),
        "claims": list(src.get("claims") or []),
        "assumptions": list(src.get("assumptions") or []),
        "supporting_evidence": list(
            src.get("evidence") or src.get("supporting_evidence") or []
        ),
        "contradictory_evidence": list(
            src.get("negative_evidence")
            or src.get("contradictory_evidence")
            or []
        ),
        "known_failure_patterns": list(src.get("known_failure_patterns") or []),
        "kill_conditions": list(
            src.get("kill_conditions")
            or ([src["stop_condition"]] if src.get("stop_condition") else [])
        ),
        "resurrection_conditions": list(
            src.get("resurrection_conditions")
            or ([src["resume_condition"]] if src.get("resume_condition") else [])
        ),
        "required_gates": gates,
        "search_family": deepcopy(search),
        "next_decisive_question": (
            src.get("next_decisive_question")
            or src.get("next_decisive_test")
            or src.get("open_question")
        ),
        "dependencies": list(src.get("dependencies") or []),
        "blockers": list(src.get("blockers") or []),
        "point_in_time_cutoff": (
            src.get("point_in_time_cutoff")
            or src.get("prospective_cutoff")
            or src.get("discovery_cutoff")
        ),
        "source_commit": source_commit,
        "updated_at": src.get("updated_at"),
    }
