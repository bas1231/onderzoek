from __future__ import annotations

from copy import deepcopy
from typing import Any

from .hypothesis_accounting import normalize as normalize_search_family

DEFAULT_GATES = [
    "source_provenance", "point_in_time", "mechanism", "signal_edge",
    "market_edge", "execution_reality", "prebuild_killer",
    "chief_falsifier", "independent_reproduction", "validation",
    "holdout", "shadow",
]

ALLOWED_QUEUE_STATUS = {
    "QUEUED", "NEEDS_DIRECTOR", "EXPERIMENT_REQUIRED", "RUNNING",
    "WAITING_FOR_DATA", "WAITING_FOR_RESULT", "RESULT_READY",
    "NEEDS_REVISION", "PARKED", "CLOSED_NEGATIVE", "PROMOTION_CANDIDATE",
}
ALLOWED_PRIORITY = {"P0", "P1", "P2", "P3"}
NEGATIVE_DECISIONS = {"FALSIFIED", "TESTED_NEGATIVE", "CLOSED_NEGATIVE"}
NON_PROVEN_POSITIVE_DECISIONS = {
    "RESEARCH_POSITIVE": "RESEARCH_POSITIVE",
    "STRUCTURAL_CANDIDATE": "STRUCTURAL_CANDIDATE",
}
PRESERVABLE_ECONOMIC_STATES = {
    "NO_PROVEN_EDGE", "RESEARCH_POSITIVE", "STRUCTURAL_CANDIDATE",
    "EXECUTION_BLOCKED", "TESTED_NEGATIVE",
}


def _state_text(value: Any, key: str, *, default: str = "") -> str:
    if value is None:
        return default
    if not isinstance(value, str):
        raise ValueError(f"{key}_must_be_string_or_null")
    return value.strip().upper()


def _gate_status(value: Any) -> str:
    if value is None:
        return "PENDING"
    if not isinstance(value, str):
        raise ValueError("gate_status_must_be_string_or_null")
    text = value.strip().upper()
    if text == "PASS":
        return "PASS"
    if text in {"FAIL", "FAILED", "FALSIFIED", "NEGATIVE"}:
        return "FAIL"
    if text in {"N/A", "NA", "NOT_APPLICABLE"}:
        return "NOT_APPLICABLE"
    if text in {"UNKNOWN", "UNPROVEN"}:
        return "UNKNOWN"
    # Legacy qualified states (for example PASS_DISCOVERY_ONLY or
    # PENDING_PROSPECTIVE) deliberately do not count as a current PASS.
    return "PENDING"


def _merged_gates(src: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    canonical = src.get("required_gates")
    legacy = src.get("gates")
    if canonical is not None and not isinstance(canonical, dict):
        raise ValueError("required_gates_must_be_object")
    if legacy is not None and not isinstance(legacy, dict):
        raise ValueError("gates_must_be_object")

    # Legacy is the fallback representation. Canonical state is newer and must
    # win on conflicts; otherwise a stale legacy field can erase a current FAIL.
    if isinstance(legacy, dict):
        merged.update(legacy)
    if isinstance(canonical, dict):
        merged.update(canonical)
    return merged


def _economic_status(src: dict[str, Any]) -> str:
    decision = _state_text(src.get("decision"), "decision")
    queue_status = _state_text(
        src.get("queue_status"),
        "queue_status",
        default="NEEDS_DIRECTOR",
    )
    raw = _state_text(src.get("economic_status"), "economic_status")

    if (
        queue_status == "CLOSED_NEGATIVE"
        or decision in NEGATIVE_DECISIONS
        or raw == "TESTED_NEGATIVE"
    ):
        return "TESTED_NEGATIVE"
    if decision == "EXECUTION_BLOCKED" or raw == "EXECUTION_BLOCKED":
        return "EXECUTION_BLOCKED"
    if decision in NON_PROVEN_POSITIVE_DECISIONS:
        return NON_PROVEN_POSITIVE_DECISIONS[decision]
    if raw in PRESERVABLE_ECONOMIC_STATES:
        return raw
    return "NO_PROVEN_EDGE"


def _required_text(src: dict[str, Any], key: str) -> str:
    value = src.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key}_required")
    return value.strip()


def _optional_text(value: Any, key: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key}_must_be_string_or_null")
    text = value.strip()
    return text or None


def _list(src: dict[str, Any], key: str, *, allow_objects: bool = False) -> list[Any]:
    value = src.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{key}_must_be_list")
    out = deepcopy(value)
    if allow_objects:
        for index, item in enumerate(out):
            if not isinstance(item, (str, dict)):
                raise ValueError(f"{key}_item_invalid:{index}")
            if isinstance(item, str) and not item.strip():
                raise ValueError(f"{key}_item_blank:{index}")
        return out
    for index, item in enumerate(out):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{key}_item_invalid:{index}")
        out[index] = item.strip()
    return out


def _legacy_single_or_list(src: dict[str, Any], list_key: str, single_key: str) -> list[str]:
    if src.get(list_key) is not None:
        return _list(src, list_key)
    single = src.get(single_key)
    if single is None:
        return []
    if not isinstance(single, str) or not single.strip():
        raise ValueError(f"{single_key}_must_be_nonempty_string")
    return [single.strip()]


def canonicalize(candidate: dict[str, Any], source_commit: str, version: int = 1) -> dict[str, Any]:
    """Create a conservative, type-strict canonical candidate view."""
    if not isinstance(candidate, dict):
        raise ValueError("candidate_must_be_object")
    src = deepcopy(candidate)
    cid = _required_text(src, "candidate_id")
    hypothesis = _required_text(src, "hypothesis")
    if not isinstance(source_commit, str) or not source_commit.strip():
        raise ValueError("source_commit_required")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise ValueError("version_must_be_positive_integer")

    raw_gates = _merged_gates(src)
    for name in raw_gates:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("gate_name_must_be_nonempty_string")
    gates = {name: _gate_status(raw_gates.get(name)) for name in DEFAULT_GATES}
    for name, value in raw_gates.items():
        gate_name = name.strip()
        gates.setdefault(gate_name, _gate_status(value))

    raw_queue = _state_text(
        src.get("queue_status"),
        "queue_status",
        default="NEEDS_DIRECTOR",
    )
    queue_status = raw_queue if raw_queue in ALLOWED_QUEUE_STATUS else "NEEDS_DIRECTOR"
    raw_priority = _state_text(src.get("priority"), "priority", default="P3")
    priority = raw_priority if raw_priority in ALLOWED_PRIORITY else "P3"

    evidence_value = (
        src.get("evidence")
        if src.get("evidence") is not None
        else src.get("supporting_evidence")
    )
    negative_value = (
        src.get("negative_evidence")
        if src.get("negative_evidence") is not None
        else src.get("contradictory_evidence")
    )
    evidence_src = {"value": evidence_value}
    negative_src = {"value": negative_value}

    search = src.get("search_family")
    normalized_search = normalize_search_family(search) if search is not None else None

    next_question = (
        src.get("next_decisive_question")
        if src.get("next_decisive_question") is not None
        else src.get("next_decisive_test")
        if src.get("next_decisive_test") is not None
        else src.get("open_question")
    )
    cutoff = (
        src.get("point_in_time_cutoff")
        if src.get("point_in_time_cutoff") is not None
        else src.get("prospective_cutoff")
        if src.get("prospective_cutoff") is not None
        else src.get("discovery_cutoff")
    )

    return {
        "candidate_id": cid,
        "version": version,
        "hypothesis": hypothesis,
        "mechanism": _optional_text(src.get("mechanism"), "mechanism"),
        "phase": _optional_text(src.get("phase"), "phase") or "DISCOVERED",
        "queue_status": queue_status,
        "economic_status": _economic_status(src),
        "priority": priority,
        "claims": _list(src, "claims", allow_objects=True),
        "assumptions": _list(src, "assumptions", allow_objects=True),
        "supporting_evidence": _list(evidence_src, "value", allow_objects=True),
        "contradictory_evidence": _list(negative_src, "value", allow_objects=True),
        "known_failure_patterns": _list(src, "known_failure_patterns"),
        "kill_conditions": _legacy_single_or_list(src, "kill_conditions", "stop_condition"),
        "resurrection_conditions": _legacy_single_or_list(
            src,
            "resurrection_conditions",
            "resume_condition",
        ),
        "required_gates": gates,
        "search_family": normalized_search,
        "next_decisive_question": _optional_text(
            next_question,
            "next_decisive_question",
        ),
        "dependencies": _list(src, "dependencies"),
        "blockers": _list(src, "blockers"),
        "point_in_time_cutoff": _optional_text(
            cutoff,
            "point_in_time_cutoff",
        ),
        "source_commit": source_commit.strip(),
        "updated_at": _optional_text(src.get("updated_at"), "updated_at"),
    }
