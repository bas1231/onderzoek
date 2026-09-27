from __future__ import annotations

from statistics import mean
from typing import Any


GROUND_TRUTH_CLASSES = {"SURVIVOR", "DECISIVE_NEGATIVE"}
COUNT_FIELDS = [
    "worker_runs",
    "unique_relevant_evidence",
    "duplicate_research_items",
    "research_items",
    "contradictions_found",
    "failure_patterns_before_expensive_work",
    "applicable_known_failure_patterns",
    "queue_starvation_events",
]


def _ratio(num: float, den: float) -> float | None:
    if den <= 0:
        return None
    return round(num / den, 6)


def _numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _nonnegative_int(
    row: dict[str, Any],
    key: str,
    errors: list[str],
    case_label: str,
) -> int:
    value = row.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        errors.append(f"invalid_nonnegative_int:{case_label}:{key}")
        return 0
    return value


def _nonempty_text(
    row: dict[str, Any],
    key: str,
    errors: list[str],
    case_label: str,
) -> str | None:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"invalid_text:{case_label}:{key}")
        return None
    return value.strip()


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate frozen shadow metrics without inventing a composite score.

    Input is deliberately type-strict. Malformed benchmark records remain
    visible as validation errors rather than being coerced or silently dropped.
    Baseline/challenger comparability is later checked on both case IDs and the
    frozen per-case experiment metadata.
    """
    if not isinstance(records, list):
        raise ValueError("benchmark_records_must_be_list")

    validation_errors: list[str] = []
    rows: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            validation_errors.append(f"record_must_be_object:{index}")
            continue
        rows.append(record)

    worker_runs = 0
    unique_evidence = 0
    duplicate_work = 0
    total_research = 0
    contradictions = 0
    failures_pre = 0
    applicable_failures = 0
    provenance_pass = 0
    starvation = 0
    survivor_total = 0
    survivor_kept = 0
    negative_total = 0
    false_survivors = 0
    steps: list[int] = []

    source_families: set[str] = set()
    overhead: list[float] = []
    usage: list[float] = []
    hard_failures: list[str] = []
    task_shapes: set[str] = set()
    case_ids: list[str] = []
    case_signatures: list[dict[str, str]] = []
    active_hour_ids: set[str] = set()

    for index, row in enumerate(rows):
        provisional_id = row.get("case_id")
        case_label = (
            provisional_id.strip()
            if isinstance(provisional_id, str) and provisional_id.strip()
            else f"row-{index}"
        )

        case_id = _nonempty_text(row, "case_id", validation_errors, case_label)
        active_hour_id = _nonempty_text(
            row, "active_hour_id", validation_errors, case_label
        )
        task_shape = _nonempty_text(row, "task_shape", validation_errors, case_label)
        ground_truth = _nonempty_text(
            row, "ground_truth_class", validation_errors, case_label
        )
        decision = _nonempty_text(row, "decision", validation_errors, case_label)

        if ground_truth is not None and ground_truth not in GROUND_TRUTH_CLASSES:
            validation_errors.append(
                f"invalid_ground_truth_class:{case_label}:{ground_truth}"
            )

        counts = {
            key: _nonnegative_int(row, key, validation_errors, case_label)
            for key in COUNT_FIELDS
        }
        worker_runs += counts["worker_runs"]
        unique_evidence += counts["unique_relevant_evidence"]
        duplicate_work += counts["duplicate_research_items"]
        total_research += counts["research_items"]
        contradictions += counts["contradictions_found"]
        failures_pre += counts["failure_patterns_before_expensive_work"]
        applicable_failures += counts["applicable_known_failure_patterns"]
        starvation += counts["queue_starvation_events"]

        if counts["duplicate_research_items"] > counts["research_items"]:
            validation_errors.append(
                f"duplicate_items_exceed_research_items:{case_label}"
            )
        if (
            counts["failure_patterns_before_expensive_work"]
            > counts["applicable_known_failure_patterns"]
        ):
            validation_errors.append(
                f"predetected_failures_exceed_applicable:{case_label}"
            )

        provenance = row.get("point_in_time_and_provenance_complete")
        if not isinstance(provenance, bool):
            validation_errors.append(
                f"invalid_boolean:{case_label}:point_in_time_and_provenance_complete"
            )
        elif provenance:
            provenance_pass += 1

        if ground_truth == "SURVIVOR":
            survivor_total += 1
            if decision != "KILL":
                survivor_kept += 1
        elif ground_truth == "DECISIVE_NEGATIVE":
            negative_total += 1
            if decision not in {"KILL", "CLOSED_NEGATIVE"}:
                false_survivors += 1
            step_value = row.get("steps_to_decisive_falsification")
            if step_value is not None:
                if (
                    not isinstance(step_value, int)
                    or isinstance(step_value, bool)
                    or step_value < 0
                ):
                    validation_errors.append(
                        f"invalid_nonnegative_int:{case_label}:steps_to_decisive_falsification"
                    )
                else:
                    steps.append(step_value)

        families = row.get("source_families_covered")
        if not isinstance(families, list):
            validation_errors.append(
                f"source_families_must_be_list:{case_label}"
            )
        else:
            for family in families:
                if not isinstance(family, str) or not family.strip():
                    validation_errors.append(
                        f"invalid_source_family:{case_label}"
                    )
                else:
                    source_families.add(family.strip())

        failures = row.get("hard_failures")
        if not isinstance(failures, list):
            validation_errors.append(f"hard_failures_must_be_list:{case_label}")
        else:
            for failure in failures:
                if not isinstance(failure, str) or not failure.strip():
                    validation_errors.append(f"invalid_hard_failure:{case_label}")
                else:
                    hard_failures.append(failure.strip())

        for key, destination in [
            ("coordination_overhead_units", overhead),
            ("plan_usage_units", usage),
        ]:
            value = row.get(key)
            if value is None:
                continue
            if not _numeric(value) or value < 0:
                validation_errors.append(f"invalid_nonnegative_number:{case_label}:{key}")
            else:
                destination.append(float(value))

        if case_id is not None:
            case_ids.append(case_id)
        if active_hour_id is not None:
            active_hour_ids.add(active_hour_id)
        if task_shape is not None:
            task_shapes.add(task_shape)
        if (
            case_id is not None
            and active_hour_id is not None
            and task_shape is not None
            and ground_truth in GROUND_TRUTH_CLASSES
        ):
            case_signatures.append(
                {
                    "case_id": case_id,
                    "active_hour_id": active_hour_id,
                    "task_shape": task_shape,
                    "ground_truth_class": ground_truth,
                }
            )

    case_id_complete = len(case_ids) == len(rows)
    case_id_unique = len(set(case_ids)) == len(case_ids)
    case_metadata_complete = len(case_signatures) == len(rows)

    if rows and not case_id_complete:
        validation_errors.append("missing_case_id")
    if not case_id_unique:
        validation_errors.append("duplicate_case_id")
    if rows and not case_metadata_complete:
        validation_errors.append("incomplete_case_metadata")
    if worker_runs <= 0:
        validation_errors.append("missing_worker_run_denominator")
    if total_research <= 0:
        validation_errors.append("missing_research_item_denominator")
    if survivor_total <= 0:
        validation_errors.append("missing_survivor_case")
    if negative_total <= 0:
        validation_errors.append("missing_decisive_negative_case")

    return {
        "observation_count": len(rows),
        "input_record_count": len(records),
        "case_ids": sorted(case_ids),
        "case_signatures": sorted(
            case_signatures,
            key=lambda row: (
                row["case_id"],
                row["active_hour_id"],
                row["task_shape"],
                row["ground_truth_class"],
            ),
        ),
        "case_id_complete": case_id_complete,
        "case_id_unique": case_id_unique,
        "case_metadata_complete": case_metadata_complete,
        "validation_errors": sorted(set(validation_errors)),
        "active_hour_cycles": len(active_hour_ids),
        "task_shapes_seen": sorted(task_shapes),
        "M1_unique_relevant_evidence_per_worker_run": _ratio(unique_evidence, worker_runs),
        "M2_duplicate_research_ratio": _ratio(duplicate_work, total_research),
        "M3_mean_steps_to_decisive_falsification": (
            round(mean(steps), 6) if steps else None
        ),
        "M4_failure_pattern_pre_detection_ratio": _ratio(
            failures_pre, applicable_failures
        ),
        "M5_survivor_preservation_ratio": _ratio(survivor_kept, survivor_total),
        "M6_false_survivors": false_survivors,
        "M6_false_survivor_rate": _ratio(false_survivors, negative_total),
        "M7_contradictions_found": contradictions,
        "M8_point_in_time_and_provenance_completeness": _ratio(
            provenance_pass, len(rows)
        ),
        "M9_source_family_coverage": len(source_families),
        "M10_queue_starvation_events": starvation,
        "M11_mean_coordination_overhead": (
            round(mean(overhead), 6) if overhead else None
        ),
        "M12_mean_plan_usage": round(mean(usage), 6) if usage else None,
        "survivor_cases": survivor_total,
        "decisive_negative_cases": negative_total,
        "hard_failures": sorted(set(hard_failures)),
    }


def _minimum_set(summary: dict[str, Any]) -> bool:
    return (
        summary.get("observation_count", 0) >= 20
        and summary.get("input_record_count") == summary.get("observation_count")
        and summary.get("active_hour_cycles", 0) >= 10
        and len(summary.get("task_shapes_seen") or []) >= 2
        and summary.get("survivor_cases", 0) >= 1
        and summary.get("decisive_negative_cases", 0) >= 1
        and summary.get("case_id_complete") is True
        and summary.get("case_id_unique") is True
        and summary.get("case_metadata_complete") is True
        and not summary.get("validation_errors")
    )


def replacement_check(
    baseline: dict[str, Any], challenger: dict[str, Any]
) -> dict[str, Any]:
    """Apply preregistered replacement rules with fail-closed comparability.

    A challenger cannot win by dropping hard cases, changing the observation
    set, relabeling case metadata, or presenting malformed/missing values as
    favorable metrics.
    """
    challenger_hard = list(challenger.get("hard_failures") or [])
    baseline_minimum = _minimum_set(baseline)
    challenger_minimum = _minimum_set(challenger)

    baseline_cases = baseline.get("case_ids") or []
    challenger_cases = challenger.get("case_ids") or []
    comparable_case_set = (
        bool(baseline_cases)
        and baseline_cases == challenger_cases
        and baseline.get("observation_count") == challenger.get("observation_count")
    )
    baseline_signatures = baseline.get("case_signatures") or []
    challenger_signatures = challenger.get("case_signatures") or []
    comparable_case_metadata = (
        bool(baseline_signatures)
        and baseline_signatures == challenger_signatures
        and baseline.get("case_metadata_complete") is True
        and challenger.get("case_metadata_complete") is True
    )

    regression_pairs = [
        (
            "M5_survivor_preservation_ratio",
            baseline.get("M5_survivor_preservation_ratio"),
            challenger.get("M5_survivor_preservation_ratio"),
            "HIGH",
        ),
        (
            "M6_false_survivor_rate",
            baseline.get("M6_false_survivor_rate"),
            challenger.get("M6_false_survivor_rate"),
            "LOW",
        ),
        (
            "M8_point_in_time_and_provenance_completeness",
            baseline.get("M8_point_in_time_and_provenance_completeness"),
            challenger.get("M8_point_in_time_and_provenance_completeness"),
            "HIGH",
        ),
    ]

    regression_metrics_complete = all(
        _numeric(b) and _numeric(c) for _, b, c, _ in regression_pairs
    )
    no_regression = regression_metrics_complete and all(
        (direction == "HIGH" and c >= b)
        or (direction == "LOW" and c <= b)
        for _, b, c, direction in regression_pairs
    )

    improvements: list[str] = []
    comparisons = [
        ("M1", "M1_unique_relevant_evidence_per_worker_run", "HIGH"),
        ("M2", "M2_duplicate_research_ratio", "LOW"),
        ("M3", "M3_mean_steps_to_decisive_falsification", "LOW"),
        ("M7", "M7_contradictions_found", "HIGH"),
        ("M9", "M9_source_family_coverage", "HIGH"),
    ]
    for mid, key, direction in comparisons:
        b = baseline.get(key)
        c = challenger.get(key)
        if not (_numeric(b) and _numeric(c)):
            continue
        if (direction == "HIGH" and c > b) or (
            direction == "LOW" and c < b
        ):
            improvements.append(mid)

    scientific_gate = (
        baseline_minimum
        and challenger_minimum
        and comparable_case_set
        and comparable_case_metadata
        and not challenger_hard
        and no_regression
        and len(improvements) >= 2
    )

    return {
        "baseline_minimum_observation_set_met": baseline_minimum,
        "challenger_minimum_observation_set_met": challenger_minimum,
        "minimum_observation_set_met": baseline_minimum and challenger_minimum,
        "comparable_case_set": comparable_case_set,
        "comparable_case_metadata": comparable_case_metadata,
        "hard_fail_clear": not challenger_hard,
        "regression_metrics_complete": regression_metrics_complete,
        "no_material_regression_gate": no_regression,
        "strict_improvements": improvements,
        "strict_improvement_count": len(improvements),
        "scientific_replacement_gate_met": scientific_gate,
        "automatic_runtime_replacement_authorized": False,
        "requires_human_integration_decision": True,
    }
