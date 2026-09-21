from __future__ import annotations

from copy import deepcopy
from typing import Any

DEFAULT_GATES = [
    "source_provenance", "point_in_time", "mechanism", "signal_edge",
    "market_edge", "execution_reality", "prebuild_killer",
    "chief_falsifier", "independent_reproduction", "validation",
    "holdout", "shadow",
]

ECONOMIC_MAP = {
    "FALSIFIED": "TESTED_NEGATIVE",
    "TESTED_NEGATIVE": "TESTED_NEGATIVE",
    "CLOSED_NEGATIVE": "TESTED_NEGATIVE",
    "RESEARCH_POSITIVE": "RESEARCH_POSITIVE",
    "STRUCTURAL_CANDIDATE": "STRUCTURAL_CANDIDATE",
    "EXECUTION_BLOCKED": "EXECUTION_BLOCKED",
}

SAFE_NEGATIVE_STATES = {
    "TESTED_NEGATIVE",
    "EXECUTION_BLOCKED",
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


def canonicalize(candidate: dict[str, Any], source_commit: str, version: int = 1) -> dict[str, Any]:
    """Create a read-only canonical candidate view from legacy or canonical state.

    The adapter is intentionally asymmetric: it preserves explicit negative or
    blocked states, but it never upgrades an unknown candidate into a proven
    positive state merely because a legacy field is optimistic.
    """
    src = deepcopy(candidate)
    cid = str(src.get("candidate_id") or "").strip()
    if not cid:
        raise ValueError("candidate_id_required")
    if not source_commit:
        raise ValueError("source_commit_required")

    if isinstance(src.get("gates"), dict):
        raw_gates = src["gates"]
    elif isinstance(src.get("required_gates"), dict):
        raw_gates = src["required_gates"]
    else:
        raw_gates = {}

    gates = {name: _gate_status(raw_gates.get(name)) for name in DEFAULT_GATES}
    for name, value in raw_gates.items():
        gates.setdefault(str(name), _gate_status(value))

    decision = str(src.get("decision") or "").upper()
    queue_status = str(src.get("queue_status") or "NEEDS_DIRECTOR").upper()
    raw_economic = str(src.get("economic_status") or "").upper()

    economic = ECONOMIC_MAP.get(decision)
    if economic is None and queue_status == "CLOSED_NEGATIVE":
        economic = "TESTED_NEGATIVE"
    if economic is None and raw_economic in SAFE_NEGATIVE_STATES:
        economic = raw_economic
    if economic is None:
        economic = "NO_PROVEN_EDGE"

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
        "economic_status": economic,
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
