from __future__ import annotations

from collections import Counter
from typing import Any

FAILED_STATES = {"STALE", "FAILED", "ERROR", "UNAVAILABLE"}
COMMUNITY_CLASSES = {"COMMUNITY", "SOCIAL", "VIDEO"}
PRIMARY_AUTHORITIES = {"OFFICIAL_PRIMARY", "ACADEMIC_PRIMARY"}


def _optional_text(value: Any, error: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(error)
    return value.strip()


def _normalize_family(value: str) -> str:
    return value.strip().casefold()


def _string_set(values: Any, error: str) -> set[str]:
    if not isinstance(values, list):
        raise ValueError(error)
    out: set[str] = set()
    for index, value in enumerate(values):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{error}:{index}")
        out.add(_normalize_family(value))
    return out


def _optional_bool(item: dict[str, Any], key: str) -> bool | None:
    value = item.get(key)
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ValueError(f"{key}_must_be_boolean_or_null")
    return value


def _identity(item: dict[str, Any]) -> tuple[str, str] | None:
    """Return strongest available document/upstream identity.

    Content hash outranks URL/source ID so the same document mirrored at two
    locations counts once. Canonical upstream fact IDs are next best. A bare
    source ID is a last-resort retrieval identity and is not treated as strong
    independence evidence.
    """
    content_hash = _optional_text(
        item.get("document_sha256")
        if item.get("document_sha256") is not None
        else item.get("content_hash"),
        "content_hash_must_be_string_or_null",
    )
    if content_hash:
        return ("sha256", content_hash.lower())

    upstream = _optional_text(
        item.get("upstream_fact_id")
        if item.get("upstream_fact_id") is not None
        else item.get("canonical_source_id"),
        "upstream_identity_must_be_string_or_null",
    )
    if upstream:
        return ("upstream", upstream)

    source_id = _optional_text(
        item.get("source_id"),
        "source_id_must_be_string_or_null",
    )
    if source_id:
        return ("source", source_id)
    return None


def _ratio(num: int, den: int) -> float | None:
    if den <= 0:
        return None
    return round(num / den, 6)


def summarize(
    primary_items: list[dict[str, Any]],
    recon_items: list[dict[str, Any]],
    attempted_families: list[str],
    required_families: list[str],
) -> dict[str, Any]:
    """Measure discovery breadth/overlap without treating absence as success.

    A family is retrieval-complete only when at least one item explicitly says
    ``retrieval_succeeded is True`` and is not in a failed/stale state. Missing
    retrieval status remains UNKNOWN. Unidentified relevant/changed items stay
    visible but are not counted as proven-unique documents.
    """
    if not isinstance(primary_items, list) or not isinstance(recon_items, list):
        raise ValueError("discovery_items_must_be_lists")
    if not isinstance(attempted_families, list) or not isinstance(required_families, list):
        raise ValueError("source_family_inputs_must_be_lists")

    if any(not isinstance(x, dict) for x in primary_items + recon_items):
        raise ValueError("discovery_item_must_be_object")

    attempted = _string_set(attempted_families, "attempted_source_family_invalid")
    required = _string_set(required_families, "required_source_family_invalid")

    p = list(primary_items)
    r = list(recon_items)
    p_keys = {key for x in p if (key := _identity(x)) is not None}
    r_keys = {key for x in r if (key := _identity(x)) is not None}
    union = p_keys | r_keys
    overlap = p_keys & r_keys

    family_counts: Counter[str] = Counter()
    successful_family_counts: Counter[str] = Counter()
    successful_items = 0
    successful_primary_items = 0
    relevant_keys: set[tuple[str, str]] = set()
    relevant_unkeyed = 0
    unsupported_community = 0
    changed_keys: set[tuple[str, str]] = set()
    changed_unkeyed = 0
    stale_or_failed = 0
    unidentified_items = 0
    unknown_retrieval_status = 0

    for item in p + r:
        family_raw = _optional_text(
            item.get("source_family"),
            "source_family_must_be_string_or_null",
        )
        family = _normalize_family(family_raw) if family_raw else "unknown"
        family_counts[family] += 1

        state = _optional_text(
            item.get("source_state"),
            "source_state_must_be_string_or_null",
        ).upper()
        retrieval_succeeded = _optional_bool(item, "retrieval_succeeded")
        relevant = _optional_bool(item, "relevant")
        independently_supported = _optional_bool(item, "independently_supported")
        changed_or_new = _optional_bool(item, "changed_or_new")

        failed_state = state in FAILED_STATES
        if failed_state:
            stale_or_failed += 1

        success = retrieval_succeeded is True and not failed_state
        if success:
            successful_family_counts[family] += 1
            successful_items += 1
        elif retrieval_succeeded is None and not failed_state:
            unknown_retrieval_status += 1

        authority = _optional_text(
            item.get("source_authority"),
            "source_authority_must_be_string_or_null",
        ).upper()
        if success and authority in PRIMARY_AUTHORITIES:
            successful_primary_items += 1

        identity = _identity(item)
        if identity is None:
            unidentified_items += 1

        if relevant is True:
            if identity is None:
                relevant_unkeyed += 1
            else:
                relevant_keys.add(identity)

        source_class = _optional_text(
            item.get("source_class"),
            "source_class_must_be_string_or_null",
        ).upper()
        if source_class in COMMUNITY_CLASSES and independently_supported is not True:
            unsupported_community += 1

        if changed_or_new is True:
            if identity is None:
                changed_unkeyed += 1
            else:
                changed_keys.add(identity)

    successful = {
        family
        for family, count in successful_family_counts.items()
        if count > 0 and family != "unknown"
    }
    attempt_gaps = sorted(required - attempted)
    retrieval_gaps = sorted(required - successful)

    return {
        "primary_scout_items": len(p),
        "recon_scout_items": len(r),
        "identified_document_keys": len(union),
        "unidentified_items": unidentified_items,
        "unknown_retrieval_status_items": unknown_retrieval_status,
        "duplicate_cross_scout_keys": len(overlap),
        "duplicate_cross_scout_ratio": _ratio(len(overlap), len(union)),
        "primary_source_ratio": _ratio(successful_primary_items, successful_items),
        "successful_retrieval_items": successful_items,
        "unique_relevant_items_reported": len(relevant_keys),
        "unique_relevant_identified_items": len(relevant_keys),
        "relevant_unidentified_items": relevant_unkeyed,
        "changed_or_new_documents": len(changed_keys),
        "changed_or_new_unidentified_items": changed_unkeyed,
        "changed_or_new_items_reported": len(changed_keys),
        "unsupported_community_leads": unsupported_community,
        "stale_or_failed_items": stale_or_failed,
        "source_family_counts": dict(sorted(family_counts.items())),
        "successful_source_family_counts": dict(sorted(successful_family_counts.items())),
        "attempted_source_families": sorted(attempted),
        "successful_source_families": sorted(successful),
        "coverage_gaps": attempt_gaps,
        "retrieval_coverage_gaps": retrieval_gaps,
        "coverage_attempt_complete": not attempt_gaps,
        "coverage_retrieval_complete": not retrieval_gaps,
        "coverage_complete": not attempt_gaps and not retrieval_gaps,
        "raw_item_count_is_success_metric": False,
        "unidentified_items_count_as_proven_unique_documents": False,
        "missing_retrieval_status_counts_as_success": False,
        "zero_denominator_metrics_are_unknown": True,
    }
