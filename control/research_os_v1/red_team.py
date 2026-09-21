from __future__ import annotations

from copy import deepcopy
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


def _clean_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _neutral_claims(items: list[Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for item in items:
        if isinstance(item, str):
            text = item.strip()
            if text:
                out.append({"statement": text})
            continue
        if not isinstance(item, dict):
            continue
        row: dict[str, str] = {}
        claim_id = _clean_text(item.get("claim_id") or item.get("id"))
        statement = _clean_text(item.get("statement") or item.get("claim"))
        if claim_id:
            row["claim_id"] = claim_id
        if statement:
            row["statement"] = statement
        if row:
            out.append(row)
    return out


def _neutral_assumptions(items: list[Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for item in items:
        if isinstance(item, str):
            text = item.strip()
            if text:
                out.append({"statement": text})
            continue
        if not isinstance(item, dict):
            continue
        row: dict[str, str] = {}
        assumption_id = _clean_text(item.get("assumption_id") or item.get("id"))
        statement = _clean_text(item.get("statement") or item.get("assumption"))
        if assumption_id:
            row["assumption_id"] = assumption_id
        if statement:
            row["statement"] = statement
        if row:
            out.append(row)
    return out


def _evidence_refs(items: list[Any]) -> list[Any]:
    """Project evidence to provenance-only fields; never copy analysis prose."""
    out: list[Any] = []
    for item in items:
        if isinstance(item, str):
            text = item.strip()
            if text:
                out.append(text)
            continue
        if not isinstance(item, dict):
            continue
        row: dict[str, Any] = {}
        for key in ("ref", "evidence_ref", "source_ref", "source_id", "content_hash", "document_sha256"):
            value = _clean_text(item.get(key))
            if value:
                row[key] = value
        lineage = item.get("upstream_source_ids") or item.get("source_lineage_ids")
        if isinstance(lineage, (list, tuple, set)):
            clean = sorted({_clean_text(v) for v in lineage if _clean_text(v)})
            if clean:
                row["upstream_source_ids"] = clean
        if item.get("is_primary_source") is True:
            row["is_primary_source"] = True
        if row:
            out.append(row)
    return out


def build_blind_packet(candidate: dict[str, Any]) -> dict[str, Any]:
    """Construct adversarial input while excluding persuasive origin reasoning."""
    if not isinstance(candidate, dict):
        raise ValueError("candidate_must_be_object")
    candidate_id = _clean_text(candidate.get("candidate_id"))
    if not candidate_id:
        raise ValueError("candidate_id_required")

    search_family = candidate.get("search_family")
    if search_family is not None and not isinstance(search_family, dict):
        raise ValueError("search_family_must_be_object_or_null")

    return {
        "candidate_id": candidate_id,
        "claim": _clean_text(candidate.get("hypothesis")),
        "mechanism_statement": _clean_text(candidate.get("mechanism")),
        "claims": _neutral_claims(list(candidate.get("claims") or [])),
        "assumptions": _neutral_assumptions(list(candidate.get("assumptions") or [])),
        "supporting_evidence_refs": _evidence_refs(list(candidate.get("supporting_evidence") or [])),
        "contradictory_evidence_refs": _evidence_refs(list(candidate.get("contradictory_evidence") or [])),
        "required_gates": deepcopy(candidate.get("required_gates") or {}),
        "known_failure_patterns": sorted({str(v) for v in candidate.get("known_failure_patterns") or [] if str(v)}),
        "point_in_time_cutoff": candidate.get("point_in_time_cutoff"),
        "search_family": deepcopy(search_family),
        "attack_order": list(ATTACK_ORDER),
        "allowed_verdicts": ["KILL", "PARK", "NEEDS_EVIDENCE", "SURVIVED_RED_TEAM"],
        "economic_promotion_authority": False,
        "origin_reasoning_included": False,
        "origin_confidence_included": False,
        "expected_result_included": False,
    }
