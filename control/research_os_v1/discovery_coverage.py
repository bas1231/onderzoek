from __future__ import annotations

from collections import Counter
from typing import Any


def _key(item: dict[str, Any]) -> tuple[str, str]:
    return (str(item.get("source_id") or ""), str(item.get("document_sha256") or ""))


def summarize(
    primary_items: list[dict[str, Any]],
    recon_items: list[dict[str, Any]],
    attempted_families: list[str],
    required_families: list[str],
) -> dict[str, Any]:
    """Measure discovery breadth and overlap without treating raw count as quality."""
    p = [x for x in primary_items if isinstance(x, dict)]
    r = [x for x in recon_items if isinstance(x, dict)]
    p_keys = {_key(x) for x in p if any(_key(x))}
    r_keys = {_key(x) for x in r if any(_key(x))}
    union = p_keys | r_keys
    overlap = p_keys & r_keys

    family_counts = Counter()
    primary_count = 0
    relevant_count = 0
    unsupported_community = 0
    changed_count = 0
    stale_or_failed = 0

    for item in p + r:
        family = str(item.get("source_family") or "UNKNOWN")
        family_counts[family] += 1
        if str(item.get("source_authority") or "").upper() in {"OFFICIAL_PRIMARY", "ACADEMIC_PRIMARY"}:
            primary_count += 1
        if item.get("relevant") is True:
            relevant_count += 1
        if str(item.get("source_class") or "").upper() in {"COMMUNITY", "SOCIAL", "VIDEO"} and item.get("independently_supported") is not True:
            unsupported_community += 1
        if item.get("changed_or_new") is True:
            changed_count += 1
        if str(item.get("source_state") or "").upper() in {"STALE", "FAILED", "ERROR", "UNAVAILABLE"}:
            stale_or_failed += 1

    attempted = set(map(str, attempted_families))
    required = set(map(str, required_families))
    gaps = sorted(required - attempted)
    denom = len(p) + len(r)
    overlap_ratio = (len(overlap) / max(1, len(union)))

    return {
        "primary_scout_items": len(p),
        "recon_scout_items": len(r),
        "unique_document_keys": len(union),
        "duplicate_cross_scout_keys": len(overlap),
        "duplicate_cross_scout_ratio": round(overlap_ratio, 6),
        "primary_source_ratio": round(primary_count / max(1, denom), 6),
        "unique_relevant_items_reported": relevant_count,
        "changed_or_new_documents": changed_count,
        "unsupported_community_leads": unsupported_community,
        "stale_or_failed_items": stale_or_failed,
        "source_family_counts": dict(sorted(family_counts.items())),
        "attempted_source_families": sorted(attempted),
        "coverage_gaps": gaps,
        "coverage_complete": not gaps,
        "raw_item_count_is_success_metric": False,
    }
