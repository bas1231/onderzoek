from __future__ import annotations

from statistics import mean
from typing import Any


def _ratio(num: float, den: float) -> float:
    return round(num / den, 6) if den else 0.0


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate frozen shadow metrics without inventing a composite score.

    Each record is one baseline or challenger candidate-event observation.
    The caller is responsible for preserving all preregistered cases.
    """
    rows = [r for r in records if isinstance(r, dict)]
    worker_runs = sum(int(r.get("worker_runs") or 0) for r in rows)
    unique_evidence = sum(int(r.get("unique_relevant_evidence") or 0) for r in rows)
    duplicate_work = sum(int(r.get("duplicate_research_items") or 0) for r in rows)
    total_research = sum(int(r.get("research_items") or 0) for r in rows)
    contradictions = sum(int(r.get("contradictions_found") or 0) for r in rows)
    failures_pre = sum(int(r.get("failure_patterns_before_expensive_work") or 0) for r in rows)
    applicable_failures = sum(int(r.get("applicable_known_failure_patterns") or 0) for r in rows)
    provenance_pass = sum(1 for r in rows if r.get("point_in_time_and_provenance_complete") is True)
    starvation = sum(int(r.get("queue_starvation_events") or 0) for r in rows)
    survivor_total = sum(1 for r in rows if r.get("ground_truth_class") == "SURVIVOR")
    survivor_kept = sum(1 for r in rows if r.get("ground_truth_class") == "SURVIVOR" and r.get("decision") != "KILL")
    negative_total = sum(1 for r in rows if r.get("ground_truth_class") == "DECISIVE_NEGATIVE")
    false_survivors = sum(1 for r in rows if r.get("ground_truth_class") == "DECISIVE_NEGATIVE" and r.get("decision") not in {"KILL", "CLOSED_NEGATIVE"})
    steps = [int(r["steps_to_decisive_falsification"]) for r in rows if r.get("ground_truth_class") == "DECISIVE_NEGATIVE" and r.get("steps_to_decisive_falsification") is not None]
    source_families = set()
    overhead = []
    usage = []
    hard_failures = []
    task_shapes = set()

    for r in rows:
        source_families.update(map(str, r.get("source_families_covered") or []))
        if r.get("coordination_overhead_units") is not None:
            overhead.append(float(r["coordination_overhead_units"]))
        if r.get("plan_usage_units") is not None:
            usage.append(float(r["plan_usage_units"]))
        hard_failures.extend(map(str, r.get("hard_failures") or []))
        if r.get("task_shape"):
            task_shapes.add(str(r["task_shape"]))

    return {
        "observation_count": len(rows),
        "active_hour_cycles": len({str(r.get("active_hour_id")) for r in rows if r.get("active_hour_id")}),
        "task_shapes_seen": sorted(task_shapes),
        "M1_unique_relevant_evidence_per_worker_run": _ratio(unique_evidence, worker_runs),
        "M2_duplicate_research_ratio": _ratio(duplicate_work, total_research),
        "M3_mean_steps_to_decisive_falsification": round(mean(steps), 6) if steps else None,
        "M4_failure_pattern_pre_detection_ratio": _ratio(failures_pre, applicable_failures),
        "M5_survivor_preservation_ratio": _ratio(survivor_kept, survivor_total),
        "M6_false_survivors": false_survivors,
        "M7_contradictions_found": contradictions,
        "M8_point_in_time_and_provenance_completeness": _ratio(provenance_pass, len(rows)),
        "M9_source_family_coverage": len(source_families),
        "M10_queue_starvation_events": starvation,
        "M11_mean_coordination_overhead": round(mean(overhead), 6) if overhead else None,
        "M12_mean_plan_usage": round(mean(usage), 6) if usage else None,
        "survivor_cases": survivor_total,
        "decisive_negative_cases": negative_total,
        "hard_failures": sorted(hard_failures),
    }


def replacement_check(baseline: dict[str, Any], challenger: dict[str, Any]) -> dict[str, Any]:
    """Apply only preregistered qualitative replacement rules; no weighted score."""
    hard = list(challenger.get("hard_failures") or [])
    no_regression = (
        challenger.get("M5_survivor_preservation_ratio", 0) >= baseline.get("M5_survivor_preservation_ratio", 0)
        and challenger.get("M6_false_survivors", 0) <= baseline.get("M6_false_survivors", 0)
        and challenger.get("M8_point_in_time_and_provenance_completeness", 0) >= baseline.get("M8_point_in_time_and_provenance_completeness", 0)
    )
    improvements = []
    comparisons = [
        ("M1", "M1_unique_relevant_evidence_per_worker_run", "HIGH"),
        ("M2", "M2_duplicate_research_ratio", "LOW"),
        ("M3", "M3_mean_steps_to_decisive_falsification", "LOW"),
        ("M7", "M7_contradictions_found", "HIGH"),
        ("M9", "M9_source_family_coverage", "HIGH"),
    ]
    for mid, key, direction in comparisons:
        b, c = baseline.get(key), challenger.get(key)
        if b is None or c is None:
            continue
        if (direction == "HIGH" and c > b) or (direction == "LOW" and c < b):
            improvements.append(mid)

    minimum_set = (
        challenger.get("observation_count", 0) >= 20
        and challenger.get("active_hour_cycles", 0) >= 10
        and len(challenger.get("task_shapes_seen") or []) >= 2
        and challenger.get("survivor_cases", 0) >= 1
        and challenger.get("decisive_negative_cases", 0) >= 1
    )

    return {
        "minimum_observation_set_met": minimum_set,
        "hard_fail_clear": not hard,
        "no_material_regression_gate": no_regression,
        "strict_improvements": improvements,
        "strict_improvement_count": len(improvements),
        "scientific_replacement_gate_met": minimum_set and not hard and no_regression and len(improvements) >= 2,
        "automatic_runtime_replacement_authorized": False,
        "requires_human_integration_decision": True,
    }
