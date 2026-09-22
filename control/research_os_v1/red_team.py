from __future__ import annotations

from typing import Any

from .hypothesis_accounting import normalize as normalize_search_family

ATTACK_ORDER = [
    "SEMANTIC_SOURCE",
    "TIMESTAMP_LOOKAHEAD_REVISION",
    "MECHANISM_LOGIC",
    "STATISTICAL_MULTIPLE_TESTING",
    "MARKET_EXECUTION_FRICTION",
    "REGIME_ROBUSTNESS",
    "METHODOLOGY_PROCESS",
]

REFERENCE_KEYS = (
    "ref",
    "evidence_ref",
    "source_ref",
    "source_id",
    "content_hash",
    "document_sha256",
)
SEARCH_FAMILY_FIELDS = (
    "id",
    "hypotheses_examined",
    "parameterizations_examined",
    "post_hoc_mutations",
    "failed_variants",
    "surviving_variants",
    "untouched_evidence_remaining",
    "data_periods_seen",
)


def _required_text(value: Any, error: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(error)
    return value.strip()


def _optional_text(value: Any, error: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(error)
    text = value.strip()
    return text or None


def _require_list(value: Any, error: str) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(error)
    return value


def _neutral_claims(items: list[Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for index, item in enumerate(items):
        if isinstance(item, str):
            text = item.strip()
            if not text:
                raise ValueError(f"blank_claim:{index}")
            out.append({"statement": text})
            continue
        if not isinstance(item, dict):
            raise ValueError(f"claim_must_be_string_or_object:{index}")
        row: dict[str, str] = {}
        raw_id = item.get("claim_id") if item.get("claim_id") is not None else item.get("id")
        raw_statement = item.get("statement") if item.get("statement") is not None else item.get("claim")
        claim_id = _optional_text(raw_id, f"invalid_claim_id:{index}")
        statement = _optional_text(raw_statement, f"invalid_claim_statement:{index}")
        if claim_id:
            row["claim_id"] = claim_id
        if statement:
            row["statement"] = statement
        if not row:
            raise ValueError(f"claim_has_no_neutral_content:{index}")
        out.append(row)
    return out


def _neutral_assumptions(items: list[Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for index, item in enumerate(items):
        if isinstance(item, str):
            text = item.strip()
            if not text:
                raise ValueError(f"blank_assumption:{index}")
            out.append({"statement": text})
            continue
        if not isinstance(item, dict):
            raise ValueError(f"assumption_must_be_string_or_object:{index}")
        row: dict[str, str] = {}
        raw_id = item.get("assumption_id") if item.get("assumption_id") is not None else item.get("id")
        raw_statement = item.get("statement") if item.get("statement") is not None else item.get("assumption")
        assumption_id = _optional_text(raw_id, f"invalid_assumption_id:{index}")
        statement = _optional_text(raw_statement, f"invalid_assumption_statement:{index}")
        if assumption_id:
            row["assumption_id"] = assumption_id
        if statement:
            row["statement"] = statement
        if not row:
            raise ValueError(f"assumption_has_no_neutral_content:{index}")
        out.append(row)
    return out


def _evidence_refs(items: list[Any]) -> list[Any]:
    """Project evidence to provenance-only fields; never copy analysis prose."""
    out: list[Any] = []
    for index, item in enumerate(items):
        if isinstance(item, str):
            text = item.strip()
            if not text:
                raise ValueError(f"blank_evidence_reference:{index}")
            out.append(text)
            continue
        if not isinstance(item, dict):
            raise ValueError(f"evidence_reference_must_be_string_or_object:{index}")

        row: dict[str, Any] = {}
        for key in REFERENCE_KEYS:
            if item.get(key) is None:
                continue
            row[key] = _required_text(
                item.get(key),
                f"invalid_evidence_reference_field:{index}:{key}",
            )

        lineage = (
            item.get("upstream_source_ids")
            if item.get("upstream_source_ids") is not None
            else item.get("source_lineage_ids")
        )
        if lineage is not None:
            if not isinstance(lineage, (list, tuple, set)):
                raise ValueError(f"invalid_evidence_lineage:{index}")
            clean: set[str] = set()
            for value in lineage:
                clean.add(
                    _required_text(value, f"invalid_evidence_lineage:{index}")
                )
            if clean:
                row["upstream_source_ids"] = sorted(clean)

        is_primary = item.get("is_primary_source")
        if is_primary is not None and not isinstance(is_primary, bool):
            raise ValueError(f"is_primary_source_must_be_boolean:{index}")
        if is_primary is True:
            row["is_primary_source"] = True

        provenance_keys = set(REFERENCE_KEYS) | {"upstream_source_ids"}
        if not any(key in row for key in provenance_keys):
            raise ValueError(f"evidence_reference_has_no_provenance:{index}")
        out.append(row)
    return out


def _blind_gate_states(value: Any) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("required_gates_must_be_object")
    out: dict[str, str] = {}
    for key in value:
        gate = _required_text(key, "gate_name_must_be_nonempty_string")
        out[gate] = "UNKNOWN"
    return dict(sorted(out.items()))


def _failure_patterns(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("known_failure_patterns_must_be_list")
    out = {
        _required_text(item, "failure_pattern_id_must_be_nonempty_string")
        for item in value
    }
    return sorted(out)


def _blind_search_family(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    normalized = normalize_search_family(value)
    if normalized is None:
        return None
    return {
        key: normalized[key]
        for key in SEARCH_FAMILY_FIELDS
        if key in normalized
    }


def build_blind_packet(candidate: dict[str, Any]) -> dict[str, Any]:
    """Construct adversarial input while excluding persuasive origin reasoning.

    Prior gate outcomes and the origin worker's evidence polarity are deliberately
    blinded. Search-family context is projected to neutral multiple-testing fields
    so methodological risk remains visible without leaking arbitrary thesis prose.
    """
    if not isinstance(candidate, dict):
        raise ValueError("candidate_must_be_object")
    candidate_id = _required_text(candidate.get("candidate_id"), "candidate_id_required")
    claim = _required_text(candidate.get("hypothesis"), "hypothesis_required")

    cutoff = _optional_text(
        candidate.get("point_in_time_cutoff"),
        "point_in_time_cutoff_must_be_string_or_null",
    )

    supporting = _evidence_refs(
        _require_list(
            candidate.get("supporting_evidence"),
            "supporting_evidence_must_be_list",
        )
    )
    contradictory = _evidence_refs(
        _require_list(
            candidate.get("contradictory_evidence"),
            "contradictory_evidence_must_be_list",
        )
    )

    return {
        "candidate_id": candidate_id,
        "claim": claim,
        "mechanism_statement": _optional_text(
            candidate.get("mechanism"),
            "mechanism_must_be_string_or_null",
        ),
        "claims": _neutral_claims(
            _require_list(candidate.get("claims"), "claims_must_be_list")
        ),
        "assumptions": _neutral_assumptions(
            _require_list(candidate.get("assumptions"), "assumptions_must_be_list")
        ),
        "evidence_refs": supporting + contradictory,
        "required_gates": _blind_gate_states(candidate.get("required_gates")),
        "known_failure_patterns": _failure_patterns(
            candidate.get("known_failure_patterns")
        ),
        "point_in_time_cutoff": cutoff,
        "search_family": _blind_search_family(candidate.get("search_family")),
        "attack_order": list(ATTACK_ORDER),
        "allowed_verdicts": ["KILL", "PARK", "NEEDS_EVIDENCE", "SURVIVED_RED_TEAM"],
        "economic_promotion_authority": False,
        "origin_reasoning_included": False,
        "origin_confidence_included": False,
        "origin_gate_states_included": False,
        "origin_evidence_polarity_included": False,
        "origin_search_family_extra_fields_included": False,
        "expected_result_included": False,
    }
