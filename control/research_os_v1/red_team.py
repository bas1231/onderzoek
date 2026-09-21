from __future__ import annotations

from typing import Any

ATTACK_ORDER = [
    "SEMANTIC_SOURCE",
    "TIMESTAMP_LOOKAHEAD_REVISION",
    "MECHANISM_LOGIC",
    "STATISTICAL_MULTIPLE_TESTING",
    "MARKET_EXECUTION_FRICTION",
    "REGIME_ROBUSTNESS",
    "METHODOLOGY_PROCESS",
]


def build_blind_packet(candidate: dict[str, Any]) -> dict[str, Any]:
    """Construct adversarial input while excluding persuasive origin reasoning."""
    return {
        "candidate_id": candidate.get("candidate_id"),
        "claim": candidate.get("hypothesis"),
        "mechanism_statement": candidate.get("mechanism"),
        "claims": list(candidate.get("claims") or []),
        "assumptions": list(candidate.get("assumptions") or []),
        "supporting_evidence_refs": list(candidate.get("supporting_evidence") or []),
        "contradictory_evidence_refs": list(candidate.get("contradictory_evidence") or []),
        "required_gates": dict(candidate.get("required_gates") or {}),
        "known_failure_patterns": list(candidate.get("known_failure_patterns") or []),
        "point_in_time_cutoff": candidate.get("point_in_time_cutoff"),
        "search_family": candidate.get("search_family"),
        "attack_order": list(ATTACK_ORDER),
        "allowed_verdicts": ["KILL", "PARK", "NEEDS_EVIDENCE", "SURVIVED_RED_TEAM"],
        "economic_promotion_authority": False,
        "origin_reasoning_included": False,
        "origin_confidence_included": False,
        "expected_result_included": False,
    }
