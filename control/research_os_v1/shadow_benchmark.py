from __future__ import annotations

from statistics import mean
from typing import Any


def _ratio(num: float, den: float) -> float | None:
    if den <= 0:
        return None
    return round(num / den, 6)


def _numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate frozen shadow metrics without inventing a composite score.

    Missing denominators remain unknown (`None`) rather than becoming a false
    zero. Case IDs are retained so the baseline/challenger comparison can prove
    that both systems were scored on the same preregistered observations.
    """
    rows = [r for r in records if isinstance(r, dict)]
    worker_runs = sum(int(r.get("worker_runs") or 0) for r in rows)
    unique_evidence = sum(int(r.get("unique_relevant_evidence") or 0) for r in rows)
    duplicate_work = sum(int(r.get("duplicate_research_items") or 0) for r in rows)
    total_research = sum(int(r.get("research_items") or 0) for r in rows)
    contradictions = sum(int(r.get("contradictions_found") or 0) for r in rows)
    failures_pre = sum(int(r.get("failure_patterns_before_expensive_work") or 0) for r in rows)
    applicable_failures = sum(int(r.get("applicable_known_failure_patterns") or 0) for r in rows)
    provenance_pass = sum(
        1
        for r in rows
        if r.get("point_in_time_and_provenance_complete") is True
    )
    starvation = sum(int(r.get("queue_starvation_events") or 0) for r in rows)
    survivor_total = sum(1 for r in rows if r.get("ground_truth_class") == "SURVIVOR")
    survivor_kept = sum(
        1
        for r in rows
        if r.get("ground_truth_class") == "SURVIVOR"
        and r.get("decision") != "KILL"
    )
    negative_total = sum(
        1 for r in rows if r.get("ground_truth_class") == "DECISIVE_NEGATIVE"
    )
    false_survivors = sum(
        1
        for r in rows
        if r.get("ground_truth_class") == "DECISIVE_NEGATIVE"
        and r.get("decision") not in {"KILL", "CLOSED_NEGATIVE"}
    )
    steps = [
        int(r["steps_to_decisive_falsification"])
        for r in rows
        if r.get("ground_truth_class") == "DECISIVE_NEGATIVE"
        and r.get("steps_to_decisive_falsification") is not None
    ]

    source_families: set[str] = set()
    overhead: list[float] = []
    usage: list[float] = []
    hard_failures: list[str] = []
    task_shapes: set[str] = set()
    case_ids: list[str] = []

    for r in rows:
        source_families.update(map(str, r.get("source_families_covered") or []))
        if r.get("coordination_overhead_units") is not None:
            overhead.append(float(r["coordination_overhead_units"]))
        if r.get("plan_usage_units") is not None:
            usage.append(float(r["plan_usage_units"]))
        hard_failures.extend(map(str, r.get("hard_failures") or []))
        if r.get("task_shape"):
            task_shapes.add(str(r["task_shape"]))
        if r.get("case_id"):
            case_ids.append(str(r["case_id"]))

    case_id_complete = len(case_ids) == len(rows)
    case_id_unique = len(set(case_ids)) == len(case_ids)

    validation_errors: list[str] = []
    if rows and not case_id_complete:
        validation_errors.append("missing_case_id")
    if not case_id_unique:
        validation_errors.append("duplicate_case_id")
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
        "case_ids": sorted(case_ids),
        "case_id_complete": case_id_complete,
        "case_id_unique": case_id_unique,
        "validation_errors": sorted(set(validation_errors)),
        "active_hour_cycles": len(
            {str(r.get("active_hour_id")) for r in rows if r.get("active_hour_id")}
        ),
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
        and summary.get("active_hour_cycles", 0) >= 10
        and len(summary.get("task_shapes_seen") or []) >= 2
        and summary.get("survivor_cases", 0) >= 1
        and summary.get("decisive_negative_cases", 0) >= 1
        and summary.get("case_id_complete") is True
        and summary.get("case_id_unique") is True
        and not summary.get("validation_errors")
    )


def replacement_check(
    baseline: dict[str, Any], challenger: dict[str, Any]
) -> dict[str, Any]:
    """Apply preregistered replacement rules with fail-closed comparability.

    A challenger cannot win by dropping hard cases, changing the observation
    set, or presenting missing denominators as favorable zeros.
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
        and not challenger_hard
        and no_regression
        and len(improvements) >= 2
    )

    return {
        "baseline_minimum_observation_set_met": baseline_minimum,
        "challenger_minimum_observation_set_met": challenger_minimum,
        "minimum_observation_set_met": baseline_minimum and challenger_minimum,
        "comparable_case_set": comparable_case_set,
        "hard_fail_clear": not challenger_hard,
        "regression_metrics_complete": regression_metrics_complete,
        "no_material_regression_gate": no_regression,
        "strict_improvements": improvements,
        "strict_improvement_count": len(improvements),
        "scientific_replacement_gate_met": scientific_gate,
        "automatic_runtime_replacement_authorized": False,
        "requires_human_integration_decision": True,
    }
