from __future__ import annotations

from copy import deepcopy
from typing import Any

from .shadow_benchmark import replacement_check, summarize


OBSERVATION_SCHEMA_VERSION = 1
SIDES = {"BASELINE", "CHALLENGER"}
DECISIONS = {"KEEP", "KILL", "CLOSED_NEGATIVE"}
COUNT_FIELDS = (
    "worker_runs",
    "unique_relevant_evidence",
    "duplicate_research_items",
    "research_items",
    "contradictions_found",
    "failure_patterns_before_expensive_work",
    "applicable_known_failure_patterns",
    "queue_starvation_events",
)
IDENTITY_FIELDS = (
    "case_id",
    "active_hour_id",
    "candidate_id",
    "task_shape",
    "representative_task_id",
    "legacy_role",
)


def _required_text(value: Any, error: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(error)
    return value.strip()


def _nonnegative_int(value: Any, error: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(error)
    return value


def _nonnegative_number_or_none(value: Any, error: str) -> float | int | None:
    if value is None:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        raise ValueError(error)
    return value


def _string_list(value: Any, error: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(error)
    out: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        text = _required_text(item, f"{error}:{index}")
        if text in seen:
            raise ValueError(f"{error}:duplicate:{text}")
        seen.add(text)
        out.append(text)
    return sorted(out)


def _cohort_maps(cohort_status: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    if not isinstance(cohort_status, dict):
        raise ValueError("cohort_status_must_be_object")
    if cohort_status.get("cohort_frozen") is not True:
        raise ValueError("cohort_not_frozen")
    if cohort_status.get("replacement_benchmark_ready") is not True:
        raise ValueError("cohort_not_ready_for_paired_observations")
    cohort_hash = _required_text(cohort_status.get("cohort_hash"), "cohort_hash_required")
    if not cohort_hash:
        raise ValueError("cohort_hash_required")

    metadata = cohort_status.get("cohort_case_metadata")
    resolutions = cohort_status.get("resolutions")
    if not isinstance(metadata, list) or not isinstance(resolutions, list):
        raise ValueError("cohort_metadata_or_resolutions_missing")

    by_case: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(metadata):
        if not isinstance(row, dict):
            raise ValueError(f"cohort_metadata_row_must_be_object:{index}")
        case_id = _required_text(row.get("case_id"), f"cohort_case_id_required:{index}")
        if case_id in by_case:
            raise ValueError(f"duplicate_cohort_case_id:{case_id}")
        normalized: dict[str, Any] = {}
        for field in IDENTITY_FIELDS:
            normalized[field] = _required_text(row.get(field), f"cohort_identity_missing:{case_id}:{field}")
        by_case[case_id] = normalized

    truth: dict[str, str] = {}
    for index, row in enumerate(resolutions):
        if not isinstance(row, dict):
            raise ValueError(f"resolution_row_must_be_object:{index}")
        case_id = _required_text(row.get("case_id"), f"resolution_case_id_required:{index}")
        if case_id not in by_case:
            raise ValueError(f"resolution_unknown_case:{case_id}")
        if case_id in truth:
            raise ValueError(f"duplicate_resolution_case:{case_id}")
        klass = row.get("ground_truth_class")
        if klass not in {"SURVIVOR", "DECISIVE_NEGATIVE"}:
            raise ValueError(f"unresolved_or_invalid_ground_truth:{case_id}:{klass}")
        truth[case_id] = klass

    if set(truth) != set(by_case):
        missing = sorted(set(by_case) - set(truth))
        raise ValueError("missing_ground_truth_cases:" + ",".join(missing))
    return by_case, truth


def _normalize_record(
    record: dict[str, Any],
    expected: dict[str, Any],
    ground_truth_class: str,
    side: str,
) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValueError("observation_record_must_be_object")
    case_id = expected["case_id"]

    for field in IDENTITY_FIELDS:
        actual = _required_text(record.get(field), f"identity_required:{side}:{case_id}:{field}")
        if actual != expected[field]:
            raise ValueError(
                f"identity_mismatch:{side}:{case_id}:{field}:{expected[field]}:{actual}"
            )

    decision = _required_text(record.get("decision"), f"decision_required:{side}:{case_id}").upper()
    if decision not in DECISIONS:
        raise ValueError(f"invalid_decision:{side}:{case_id}:{decision}")

    row: dict[str, Any] = {
        "case_id": case_id,
        "active_hour_id": expected["active_hour_id"],
        "task_shape": expected["task_shape"],
        "ground_truth_class": ground_truth_class,
        "decision": decision,
    }
    for field in COUNT_FIELDS:
        row[field] = _nonnegative_int(
            record.get(field), f"invalid_count:{side}:{case_id}:{field}"
        )

    provenance = record.get("point_in_time_and_provenance_complete")
    if not isinstance(provenance, bool):
        raise ValueError(f"provenance_boolean_required:{side}:{case_id}")
    row["point_in_time_and_provenance_complete"] = provenance

    row["source_families_covered"] = _string_list(
        record.get("source_families_covered"),
        f"source_families_invalid:{side}:{case_id}",
    )
    row["hard_failures"] = _string_list(
        record.get("hard_failures"),
        f"hard_failures_invalid:{side}:{case_id}",
    )

    steps = record.get("steps_to_decisive_falsification")
    if ground_truth_class == "DECISIVE_NEGATIVE" and decision in {"KILL", "CLOSED_NEGATIVE"}:
        row["steps_to_decisive_falsification"] = _nonnegative_int(
            steps, f"steps_required_for_falsified_negative:{side}:{case_id}"
        )
    elif steps is not None:
        row["steps_to_decisive_falsification"] = _nonnegative_int(
            steps, f"invalid_steps:{side}:{case_id}"
        )

    for optional in ("coordination_overhead_units", "plan_usage_units"):
        value = _nonnegative_number_or_none(
            record.get(optional), f"invalid_optional_metric:{side}:{case_id}:{optional}"
        )
        if value is not None:
            row[optional] = value

    return row


def normalize_observation_set(
    cohort_status: dict[str, Any],
    observation_set: dict[str, Any],
    expected_side: str,
) -> list[dict[str, Any]]:
    if expected_side not in SIDES:
        raise ValueError(f"invalid_expected_side:{expected_side}")
    metadata, truth = _cohort_maps(cohort_status)
    if not isinstance(observation_set, dict):
        raise ValueError("observation_set_must_be_object")
    if observation_set.get("schema_version") != OBSERVATION_SCHEMA_VERSION:
        raise ValueError("observation_schema_version_mismatch")
    side = _required_text(observation_set.get("side"), "observation_side_required").upper()
    if side != expected_side:
        raise ValueError(f"observation_side_mismatch:{expected_side}:{side}")
    cohort_hash = _required_text(observation_set.get("cohort_hash"), "observation_cohort_hash_required")
    if cohort_hash != cohort_status.get("cohort_hash"):
        raise ValueError("observation_cohort_hash_mismatch")

    records = observation_set.get("records")
    if not isinstance(records, list):
        raise ValueError("observation_records_must_be_list")

    supplied: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(deepcopy(records)):
        if not isinstance(record, dict):
            raise ValueError(f"observation_record_must_be_object:{index}")
        case_id = _required_text(record.get("case_id"), f"observation_case_id_required:{index}")
        if case_id not in metadata:
            raise ValueError(f"observation_unknown_case:{side}:{case_id}")
        if case_id in supplied:
            raise ValueError(f"duplicate_observation_case:{side}:{case_id}")
        supplied[case_id] = record

    expected_ids = set(metadata)
    supplied_ids = set(supplied)
    if supplied_ids != expected_ids:
        missing = sorted(expected_ids - supplied_ids)
        extra = sorted(supplied_ids - expected_ids)
        raise ValueError(
            "observation_case_set_mismatch:"
            f"{side}:missing={','.join(missing)}:extra={','.join(extra)}"
        )

    return [
        _normalize_record(supplied[case_id], metadata[case_id], truth[case_id], side)
        for case_id in sorted(expected_ids)
    ]


def build_paired_benchmark(
    cohort_status: dict[str, Any],
    baseline_observations: dict[str, Any],
    challenger_observations: dict[str, Any],
) -> dict[str, Any]:
    baseline_rows = normalize_observation_set(
        cohort_status, baseline_observations, "BASELINE"
    )
    challenger_rows = normalize_observation_set(
        cohort_status, challenger_observations, "CHALLENGER"
    )

    baseline_summary = summarize(baseline_rows)
    challenger_summary = summarize(challenger_rows)
    replacement = replacement_check(baseline_summary, challenger_summary)

    return {
        "schema_version": 1,
        "status": (
            "SCIENTIFIC_REPLACEMENT_GATE_MET"
            if replacement["scientific_replacement_gate_met"]
            else "REPLACEMENT_GATE_NOT_MET"
        ),
        "cohort_hash": cohort_status["cohort_hash"],
        "cohort_case_count": len(baseline_rows),
        "baseline": baseline_summary,
        "challenger": challenger_summary,
        "replacement_check": replacement,
        "automatic_runtime_replacement_authorized": False,
        "requires_human_integration_decision": True,
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "runtime_mutation": False,
        "economic_conclusion": "NO_PROVEN_EDGE",
    }
