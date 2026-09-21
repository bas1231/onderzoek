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


def _source_sets(items: list[Any]) -> tuple[set[str], set[str], bool]:
    """Return reference IDs, canonical upstream IDs and lineage completeness.

    Different file/document references are not enough to prove source
    independence: two derived artifacts can share one upstream feed. A positive
    independence decision therefore requires explicit upstream lineage on both
    sides. Exact shared references are still sufficient to prove dependence.
    """
    refs: set[str] = set()
    upstream: set[str] = set()
    complete = bool(items)

    for item in items:
        if isinstance(item, dict):
            ref = item.get("ref") or item.get("evidence_ref") or item.get("source_ref")
            if ref:
                refs.add(str(ref))

            lineage = (
                item.get("upstream_source_ids")
                or item.get("source_lineage_ids")
                or item.get("upstream_sources")
            )
            if isinstance(lineage, (list, tuple, set)) and lineage:
                upstream.update(str(value) for value in lineage if str(value))
                continue

            single = item.get("upstream_source_id")
            if single:
                upstream.add(str(single))
                continue

            # A primary source can name itself as canonical upstream provenance.
            if item.get("is_primary_source") is True and item.get("source_id"):
                upstream.add(str(item["source_id"]))
                continue

            complete = False
        else:
            text = str(item)
            if text:
                refs.add(text)
            complete = False

    if not upstream:
        complete = False
    return refs, upstream, complete


def source_independence(origin_sources: list[Any], reproduction_sources: list[Any]) -> dict[str, Any]:
    origin_refs, origin_upstream, origin_complete = _source_sets(origin_sources)
    repro_refs, repro_upstream, repro_complete = _source_sets(reproduction_sources)

    shared_refs = sorted(origin_refs & repro_refs)
    shared_upstream = sorted(origin_upstream & repro_upstream)
    proof_complete = origin_complete and repro_complete

    if shared_refs:
        status = "SHARED_UPSTREAM"
    elif not proof_complete:
        status = "UNKNOWN"
    elif shared_upstream:
        status = (
            "SHARED_UPSTREAM"
            if origin_upstream == repro_upstream
            else "PARTIAL"
        )
    else:
        status = "INDEPENDENT"

    return {
        "status": status,
        "shared_reference_ids": shared_refs,
        "shared_upstream_refs": shared_upstream,
        "origin_upstream_ids": sorted(origin_upstream),
        "reproduction_upstream_ids": sorted(repro_upstream),
        "independence_proof_complete": proof_complete,
        "counts_as_independent_reproduction": (
            status == "INDEPENDENT" and proof_complete
        ),
    }
