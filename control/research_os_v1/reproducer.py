from __future__ import annotations

from copy import deepcopy
from typing import Any


def _clean_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _reference_projection(items: list[Any]) -> list[Any]:
    """Keep provenance/lineage only; exclude origin analysis/confidence prose."""
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
        lineage = item.get("upstream_source_ids") or item.get("source_lineage_ids") or item.get("upstream_sources")
        if isinstance(lineage, (list, tuple, set)):
            clean = sorted({_clean_text(v) for v in lineage if _clean_text(v)})
            if clean:
                row["upstream_source_ids"] = clean
        single = _clean_text(item.get("upstream_source_id"))
        if single:
            row["upstream_source_id"] = single
        if item.get("is_primary_source") is True:
            row["is_primary_source"] = True
        if row:
            out.append(row)
    return out


def build_packet(candidate: dict[str, Any], preregistered_question: str) -> dict[str, Any]:
    if not isinstance(candidate, dict):
        raise ValueError("candidate_must_be_object")
    candidate_id = _clean_text(candidate.get("candidate_id"))
    if not candidate_id:
        raise ValueError("candidate_id_required")
    question = _clean_text(preregistered_question)
    if not question:
        raise ValueError("preregistered_question_required")

    return {
        "candidate_id": candidate_id,
        "preregistered_question": question,
        "raw_evidence_refs": _reference_projection(list(candidate.get("supporting_evidence") or [])),
        "contradictory_evidence_refs": _reference_projection(list(candidate.get("contradictory_evidence") or [])),
        "required_gates": deepcopy(candidate.get("required_gates") or {}),
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

            if item.get("is_primary_source") is True and item.get("source_id"):
                upstream.add(str(item["source_id"]))
                continue

            complete = False
        else:
            text = str(item).strip()
            if text:
                refs.add(text)
            complete = False

    if not upstream:
        complete = False
    return refs, upstream, complete


def source_independence(origin_sources: list[Any], reproduction_sources: list[Any]) -> dict[str, Any]:
    if not isinstance(origin_sources, list) or not isinstance(reproduction_sources, list):
        raise ValueError("source_sets_must_be_lists")

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
        status = "SHARED_UPSTREAM" if origin_upstream == repro_upstream else "PARTIAL"
    else:
        status = "INDEPENDENT"

    return {
        "status": status,
        "shared_reference_ids": shared_refs,
        "shared_upstream_refs": shared_upstream,
        "origin_upstream_ids": sorted(origin_upstream),
        "reproduction_upstream_ids": sorted(repro_upstream),
        "independence_proof_complete": proof_complete,
        "counts_as_independent_reproduction": status == "INDEPENDENT" and proof_complete,
    }
