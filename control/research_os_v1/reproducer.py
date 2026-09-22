from __future__ import annotations

from copy import deepcopy
from typing import Any


REFERENCE_KEYS = (
    "ref",
    "evidence_ref",
    "source_ref",
    "source_id",
    "content_hash",
    "document_sha256",
)
LINEAGE_KEYS = (
    "upstream_source_ids",
    "source_lineage_ids",
    "upstream_sources",
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


def _string_list(value: Any, error: str) -> list[str]:
    if not isinstance(value, (list, tuple, set)):
        raise ValueError(error)
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(error)
        out.append(item.strip())
    return sorted(set(out))


def _evidence_list(candidate: dict[str, Any], key: str) -> list[Any]:
    value = candidate.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{key}_must_be_list")
    return value


def _reference_projection(items: list[Any]) -> list[Any]:
    """Keep provenance/lineage only; exclude origin analysis/confidence prose.

    Malformed evidence is rejected rather than silently omitted, because dropping
    a bad provenance record could make the remaining packet look cleaner or more
    independent than the original evidence actually was.
    """
    if not isinstance(items, list):
        raise ValueError("evidence_items_must_be_list")

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
            if key not in item or item.get(key) is None:
                continue
            row[key] = _required_text(
                item.get(key),
                f"invalid_evidence_reference_field:{index}:{key}",
            )

        lineage_value = None
        lineage_key = None
        for key in LINEAGE_KEYS:
            if item.get(key) is not None:
                lineage_value = item.get(key)
                lineage_key = key
                break
        if lineage_key is not None:
            lineage = _string_list(
                lineage_value,
                f"invalid_evidence_lineage:{index}:{lineage_key}",
            )
            if lineage:
                row["upstream_source_ids"] = lineage

        if item.get("upstream_source_id") is not None:
            row["upstream_source_id"] = _required_text(
                item.get("upstream_source_id"),
                f"invalid_evidence_lineage:{index}:upstream_source_id",
            )
        if item.get("is_primary_source") is not None and not isinstance(
            item.get("is_primary_source"), bool
        ):
            raise ValueError(f"is_primary_source_must_be_boolean:{index}")
        if item.get("is_primary_source") is True:
            row["is_primary_source"] = True

        if not row:
            raise ValueError(f"evidence_reference_has_no_provenance:{index}")
        out.append(row)
    return out


def build_packet(candidate: dict[str, Any], preregistered_question: str) -> dict[str, Any]:
    if not isinstance(candidate, dict):
        raise ValueError("candidate_must_be_object")
    candidate_id = _required_text(candidate.get("candidate_id"), "candidate_id_required")
    question = _required_text(
        preregistered_question,
        "preregistered_question_required",
    )

    required_gates = candidate.get("required_gates")
    if required_gates is None:
        required_gates = {}
    if not isinstance(required_gates, dict):
        raise ValueError("required_gates_must_be_object")

    cutoff = _optional_text(
        candidate.get("point_in_time_cutoff"),
        "point_in_time_cutoff_must_be_string_or_null",
    )

    return {
        "candidate_id": candidate_id,
        "preregistered_question": question,
        "raw_evidence_refs": _reference_projection(
            _evidence_list(candidate, "supporting_evidence")
        ),
        "contradictory_evidence_refs": _reference_projection(
            _evidence_list(candidate, "contradictory_evidence")
        ),
        "required_gates": deepcopy(required_gates),
        "point_in_time_cutoff": cutoff,
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
    if not isinstance(items, list):
        raise ValueError("source_sets_must_be_lists")

    refs: set[str] = set()
    upstream: set[str] = set()
    complete = bool(items)

    for index, item in enumerate(items):
        if isinstance(item, str):
            text = item.strip()
            if not text:
                raise ValueError(f"blank_source_reference:{index}")
            refs.add(text)
            complete = False
            continue
        if not isinstance(item, dict):
            raise ValueError(f"source_reference_must_be_string_or_object:{index}")

        ref_value = None
        for key in ("ref", "evidence_ref", "source_ref"):
            if item.get(key) is not None:
                ref_value = _required_text(
                    item.get(key),
                    f"invalid_source_reference:{index}:{key}",
                )
                break
        if ref_value:
            refs.add(ref_value)

        lineage_value = None
        lineage_key = None
        for key in LINEAGE_KEYS:
            if item.get(key) is not None:
                lineage_value = item.get(key)
                lineage_key = key
                break
        if lineage_key is not None:
            lineage = _string_list(
                lineage_value,
                f"invalid_source_lineage:{index}:{lineage_key}",
            )
            if lineage:
                upstream.update(lineage)
                continue

        if item.get("upstream_source_id") is not None:
            upstream.add(
                _required_text(
                    item.get("upstream_source_id"),
                    f"invalid_source_lineage:{index}:upstream_source_id",
                )
            )
            continue

        is_primary = item.get("is_primary_source")
        if is_primary is not None and not isinstance(is_primary, bool):
            raise ValueError(f"is_primary_source_must_be_boolean:{index}")
        if is_primary is True:
            source_id = _required_text(
                item.get("source_id"),
                f"primary_source_id_required:{index}",
            )
            upstream.add(source_id)
            continue

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
