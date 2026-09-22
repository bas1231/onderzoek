from __future__ import annotations

from copy import deepcopy
from typing import Any

from .prospective_pairing import IDENTITY_FIELDS, OBSERVATION_SCHEMA_VERSION, SIDES


TELEMETRY_SCHEMA_VERSION = 1
VALID_DECISIONS = {"KEEP", "KILL", "CLOSED_NEGATIVE"}


def _text(value: Any, error: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(error)
    return value.strip()


def _list(value: Any, error: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(error)
    return value


def _unique_text_list(value: Any, error: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(_list(value, error)):
        text = _text(item, f"{error}:{index}")
        if text in seen:
            raise ValueError(f"{error}:duplicate:{text}")
        seen.add(text)
        out.append(text)
    return out


def _nonnegative_number(value: Any, error: str) -> float | int:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        raise ValueError(error)
    return value


def _metadata_map(cohort_status: dict[str, Any]) -> dict[str, dict[str, str]]:
    if not isinstance(cohort_status, dict) or cohort_status.get("cohort_frozen") is not True:
        raise ValueError("cohort_not_frozen")
    rows = cohort_status.get("cohort_case_metadata")
    if not isinstance(rows, list):
        raise ValueError("cohort_case_metadata_missing")
    out: dict[str, dict[str, str]] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"cohort_metadata_row_invalid:{index}")
        normalized: dict[str, str] = {}
        for field in IDENTITY_FIELDS:
            normalized[field] = _text(row.get(field), f"cohort_identity_missing:{index}:{field}")
        case_id = normalized["case_id"]
        if case_id in out:
            raise ValueError(f"duplicate_cohort_case_id:{case_id}")
        out[case_id] = normalized
    return out


def _evidence_metrics(case_id: str, evidence: Any) -> tuple[int, int, list[str], bool]:
    items = _list(evidence, f"evidence_must_be_list:{case_id}")
    seen_ids: set[str] = set()
    relevant_ids: set[str] = set()
    contradictions = 0
    families: set[str] = set()
    provenance_complete = True

    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"evidence_item_must_be_object:{case_id}:{index}")
        eid = _text(item.get("evidence_id"), f"evidence_id_required:{case_id}:{index}")
        if eid in seen_ids:
            raise ValueError(f"duplicate_evidence_id:{case_id}:{eid}")
        seen_ids.add(eid)
        relevant = item.get("relevant")
        contradiction = item.get("contradiction")
        pit = item.get("point_in_time_ok")
        provenance = item.get("provenance_ok")
        for key, value in (
            ("relevant", relevant),
            ("contradiction", contradiction),
            ("point_in_time_ok", pit),
            ("provenance_ok", provenance),
        ):
            if not isinstance(value, bool):
                raise ValueError(f"evidence_boolean_required:{case_id}:{eid}:{key}")
        family = _text(item.get("source_family"), f"source_family_required:{case_id}:{eid}")
        if relevant:
            relevant_ids.add(eid)
            families.add(family)
            if not pit or not provenance:
                provenance_complete = False
        if contradiction:
            contradictions += 1

    return len(relevant_ids), contradictions, sorted(families), provenance_complete


def _research_metrics(case_id: str, items_value: Any) -> tuple[int, int]:
    items = _list(items_value, f"research_items_must_be_list:{case_id}")
    seen: set[str] = set()
    duplicate_count = 0
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"research_item_must_be_object:{case_id}:{index}")
        item_id = _text(item.get("item_id"), f"research_item_id_required:{case_id}:{index}")
        if item_id in seen:
            raise ValueError(f"duplicate_research_item_id:{case_id}:{item_id}")
        seen.add(item_id)
        duplicate_of = item.get("duplicate_of")
        if duplicate_of is not None:
            _text(duplicate_of, f"duplicate_of_invalid:{case_id}:{item_id}")
            duplicate_count += 1
    return len(items), duplicate_count


def _failure_metrics(case_id: str, value: Any) -> tuple[int, int]:
    rows = _list(value, f"failure_patterns_must_be_list:{case_id}")
    seen: set[str] = set()
    applicable = 0
    pre = 0
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"failure_pattern_row_invalid:{case_id}:{index}")
        pid = _text(row.get("pattern_id"), f"failure_pattern_id_required:{case_id}:{index}")
        if pid in seen:
            raise ValueError(f"duplicate_failure_pattern:{case_id}:{pid}")
        seen.add(pid)
        is_applicable = row.get("applicable")
        detected_pre = row.get("detected_before_expensive_work")
        if not isinstance(is_applicable, bool) or not isinstance(detected_pre, bool):
            raise ValueError(f"failure_pattern_boolean_required:{case_id}:{pid}")
        if detected_pre and not is_applicable:
            raise ValueError(f"predetected_non_applicable_failure:{case_id}:{pid}")
        if is_applicable:
            applicable += 1
            if detected_pre:
                pre += 1
    return applicable, pre


def _normalize_telemetry_record(
    record: dict[str, Any], expected: dict[str, str], side: str
) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValueError("telemetry_record_must_be_object")
    case_id = expected["case_id"]
    for field in IDENTITY_FIELDS:
        actual = _text(record.get(field), f"telemetry_identity_required:{side}:{case_id}:{field}")
        if actual != expected[field]:
            raise ValueError(f"telemetry_identity_mismatch:{side}:{case_id}:{field}")

    decision = _text(record.get("decision"), f"telemetry_decision_required:{side}:{case_id}").upper()
    if decision not in VALID_DECISIONS:
        raise ValueError(f"invalid_telemetry_decision:{side}:{case_id}:{decision}")

    intentionally_unassigned = record.get("intentionally_unassigned", False)
    if not isinstance(intentionally_unassigned, bool):
        raise ValueError(f"intentionally_unassigned_must_be_bool:{side}:{case_id}")

    worker_run_ids = _unique_text_list(
        record.get("worker_run_ids"), f"worker_run_ids_invalid:{side}:{case_id}"
    )
    if intentionally_unassigned:
        if side != "CHALLENGER":
            raise ValueError(f"intentional_unassignment_only_challenger:{case_id}")
        if worker_run_ids:
            raise ValueError(f"unassigned_case_has_worker_runs:{case_id}")
        if decision != "KEEP":
            raise ValueError(f"unassigned_case_decision_must_be_keep:{case_id}")
    elif not worker_run_ids:
        raise ValueError(f"worker_run_ids_empty:{side}:{case_id}")

    unique_evidence, contradictions, families, provenance_complete = _evidence_metrics(
        case_id, record.get("evidence")
    )
    research_count, duplicate_count = _research_metrics(case_id, record.get("research_items"))
    applicable, pre = _failure_metrics(case_id, record.get("failure_patterns"))

    starvation = _unique_text_list(
        record.get("queue_starvation_event_ids"),
        f"queue_starvation_events_invalid:{side}:{case_id}",
    )
    hard_failures = _unique_text_list(
        record.get("hard_failures"), f"hard_failures_invalid:{side}:{case_id}"
    )

    if intentionally_unassigned and any(
        (unique_evidence, contradictions, research_count, duplicate_count, applicable, pre, len(starvation))
    ):
        raise ValueError(f"unassigned_case_has_research_activity:{case_id}")
    if intentionally_unassigned:
        # A scheduler that deliberately performs no research gets no provenance
        # completeness credit merely because the evidence set is empty.
        provenance_complete = False

    out: dict[str, Any] = {
        **expected,
        "decision": decision,
        "worker_runs": len(worker_run_ids),
        "unique_relevant_evidence": unique_evidence,
        "duplicate_research_items": duplicate_count,
        "research_items": research_count,
        "contradictions_found": contradictions,
        "failure_patterns_before_expensive_work": pre,
        "applicable_known_failure_patterns": applicable,
        "queue_starvation_events": len(starvation),
        "point_in_time_and_provenance_complete": provenance_complete,
        "source_families_covered": families,
        "hard_failures": hard_failures,
    }

    steps = record.get("steps_to_decisive_falsification")
    if steps is not None:
        if not isinstance(steps, int) or isinstance(steps, bool) or steps < 0:
            raise ValueError(f"invalid_falsification_steps:{side}:{case_id}")
        out["steps_to_decisive_falsification"] = steps

    for key in ("coordination_overhead_units", "plan_usage_units"):
        if key in record and record.get(key) is not None:
            out[key] = _nonnegative_number(
                record.get(key), f"invalid_telemetry_metric:{side}:{case_id}:{key}"
            )
    return out


def build_observation_set(
    cohort_status: dict[str, Any], telemetry_set: dict[str, Any], expected_side: str
) -> dict[str, Any]:
    side = expected_side.upper()
    if side not in SIDES:
        raise ValueError(f"invalid_side:{side}")
    metadata = _metadata_map(cohort_status)
    if not isinstance(telemetry_set, dict):
        raise ValueError("telemetry_set_must_be_object")
    if telemetry_set.get("schema_version") != TELEMETRY_SCHEMA_VERSION:
        raise ValueError("telemetry_schema_version_mismatch")
    supplied_side = _text(telemetry_set.get("side"), "telemetry_side_required").upper()
    if supplied_side != side:
        raise ValueError(f"telemetry_side_mismatch:{side}:{supplied_side}")
    cohort_hash = _text(telemetry_set.get("cohort_hash"), "telemetry_cohort_hash_required")
    if cohort_hash != cohort_status.get("cohort_hash"):
        raise ValueError("telemetry_cohort_hash_mismatch")

    records = telemetry_set.get("records")
    if not isinstance(records, list):
        raise ValueError("telemetry_records_must_be_list")
    by_case: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(deepcopy(records)):
        if not isinstance(record, dict):
            raise ValueError(f"telemetry_record_must_be_object:{index}")
        case_id = _text(record.get("case_id"), f"telemetry_case_id_required:{index}")
        if case_id not in metadata:
            raise ValueError(f"telemetry_unknown_case:{side}:{case_id}")
        if case_id in by_case:
            raise ValueError(f"duplicate_telemetry_case:{side}:{case_id}")
        by_case[case_id] = record

    expected_ids = set(metadata)
    if set(by_case) != expected_ids:
        missing = sorted(expected_ids - set(by_case))
        extra = sorted(set(by_case) - expected_ids)
        raise ValueError(
            f"telemetry_case_set_mismatch:{side}:missing={','.join(missing)}:extra={','.join(extra)}"
        )

    observations = [
        _normalize_telemetry_record(by_case[case_id], metadata[case_id], side)
        for case_id in sorted(expected_ids)
    ]
    return {
        "schema_version": OBSERVATION_SCHEMA_VERSION,
        "side": side,
        "cohort_hash": cohort_status["cohort_hash"],
        "records": observations,
    }
