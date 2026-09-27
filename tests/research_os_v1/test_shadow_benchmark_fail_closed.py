from copy import deepcopy

from control.research_os_v1.shadow_benchmark import replacement_check, summarize


def rows(*, better=False):
    result = []
    for i in range(20):
        ground_truth = "SURVIVOR" if i == 0 else "DECISIVE_NEGATIVE"
        result.append({
            "case_id": f"CASE-{i:02d}",
            "active_hour_id": f"H{i // 2}",
            "task_shape": "PARALLEL" if i % 2 else "SEQUENTIAL",
            "ground_truth_class": ground_truth,
            "decision": "KEEP" if ground_truth == "SURVIVOR" else "KILL",
            "worker_runs": 2,
            "unique_relevant_evidence": 3 if better else 2,
            "duplicate_research_items": 0 if better else 1,
            "research_items": 3,
            "contradictions_found": 2 if better else 1,
            "failure_patterns_before_expensive_work": 1,
            "applicable_known_failure_patterns": 1,
            "queue_starvation_events": 0,
            "point_in_time_and_provenance_complete": True,
            "steps_to_decisive_falsification": 2,
            "source_families_covered": ["OFFICIAL", "CODE"],
            "hard_failures": [],
        })
    return result


def test_same_case_ids_with_relabelled_ground_truth_are_not_comparable():
    baseline_rows = rows()
    challenger_rows = rows(better=True)
    challenger_rows[1]["ground_truth_class"] = "SURVIVOR"
    challenger_rows[1]["decision"] = "KEEP"
    verdict = replacement_check(
        summarize(baseline_rows),
        summarize(challenger_rows),
    )
    assert verdict["comparable_case_set"] is True
    assert verdict["comparable_case_metadata"] is False
    assert verdict["scientific_replacement_gate_met"] is False


def test_same_case_ids_with_changed_task_shape_are_not_comparable():
    baseline_rows = rows()
    challenger_rows = rows(better=True)
    challenger_rows[2]["task_shape"] = "DIFFERENT_SHAPE"
    verdict = replacement_check(
        summarize(baseline_rows),
        summarize(challenger_rows),
    )
    assert verdict["comparable_case_metadata"] is False
    assert verdict["scientific_replacement_gate_met"] is False


def test_string_numeric_is_validation_failure_not_coerced():
    malformed = rows()
    malformed[0]["worker_runs"] = "2"
    summary = summarize(malformed)
    assert any(
        error.endswith(":worker_runs")
        for error in summary["validation_errors"]
    )
    assert summary["input_record_count"] == 20


def test_boolean_numeric_is_validation_failure_not_one():
    malformed = rows()
    malformed[0]["research_items"] = True
    summary = summarize(malformed)
    assert any(
        error.endswith(":research_items")
        for error in summary["validation_errors"]
    )


def test_non_object_record_cannot_be_silently_dropped():
    malformed = rows()
    malformed.append("not-a-record")
    summary = summarize(malformed)
    assert summary["input_record_count"] == 21
    assert summary["observation_count"] == 20
    assert "record_must_be_object:20" in summary["validation_errors"]


def test_valid_matched_metadata_can_still_pass_scientific_gate():
    baseline = summarize(rows())
    challenger = summarize(rows(better=True))
    verdict = replacement_check(baseline, challenger)
    assert verdict["comparable_case_set"] is True
    assert verdict["comparable_case_metadata"] is True
    assert verdict["scientific_replacement_gate_met"] is True
    assert verdict["automatic_runtime_replacement_authorized"] is False
