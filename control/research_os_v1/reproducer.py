from __future__ import annotations

from typing import Any


def build_packet(candidate: dict[str, Any], preregistered_question: str) -> dict[str, Any]:
    return {
        "candidate_id": candidate.get("candidate_id"),
        "preregistered_question": preregistered_question,
        "raw_evidence_refs": list(candidate.get("supporting_evidence") or []),
        "contradictory_evidence_refs": list(candidate.get("contradictory_evidence") or []),
        "required_gates": dict(candidate.get("required_gates") or {}),
        "point_in_time_cutoff": candidate.get("point_in_time_cutoff"),
        "origin_reasoning_included": False,
        "origin_conclusion_included": False,
        "origin_confidence_included": False,
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
    }


def source_independence(origin_sources: list[str], reproduction_sources: list[str]) -> dict[str, Any]:
    origin = set(map(str, origin_sources))
    repro = set(map(str, reproduction_sources))
    shared = sorted(origin & repro)
    if not origin or not repro:
        status = "UNKNOWN"
    elif not shared:
        status = "INDEPENDENT"
    elif origin == repro:
        status = "SHARED_UPSTREAM"
    else:
        status = "PARTIAL"
    return {
        "status": status,
        "shared_upstream_refs": shared,
        "counts_as_independent_reproduction": status == "INDEPENDENT",
    }
