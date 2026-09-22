import pytest

from control.research_os_v1.prospective_metrics import build_observation_set


def cohort():
    metadata = []
    for i in range(2):
        metadata.append({
            "case_id": f"ROS1-{i:024x}",
            "active_hour_id": f"hourly-2026092{i}T120000+0200",
            "candidate_id": f"C-{i}",
            "task_shape": "LOW_SEQUENTIAL" if i == 0 else "HIGH_INDEPENDENT",
            "representative_task_id": f"hourly-2026092{i}T120000+0200:role-{i}",
            "legacy_role": "settlement" if i == 0 else "scout",
        })
    return {
        "cohort_frozen": True,
        "cohort_hash": "hash-1",
        "cohort_case_metadata": metadata,
    }


def record(meta, *, provenance=True):
    return {
        **meta,
        "decision": "KEEP",
        "worker_run_ids": ["W1", "W2"],
        # Self-reported aggregate fields must not be trusted or used.
        "unique_relevant_evidence": 999,
        "evidence": [
            {
                "evidence_id": "E1",
                "source_family": "OFFICIAL",
                "relevant": True,
                "contradiction": False,
                "point_in_time_ok": True,
                "provenance_ok": provenance,
            },
            {
                "evidence_id": "E2",
                "source_family": "CODE",
                "relevant": True,
                "contradiction": True,
                "point_in_time_ok": True,
                "provenance_ok": True,
            },
            {
                "evidence_id": "E3",
                "source_family": "COMMUNITY",
                "relevant": False,
                "contradiction": False,
                "point_in_time_ok": False,
                "provenance_ok": False,
            },
        ],
        "research_items": [
            {"item_id": "R1", "duplicate_of": None},
            {"item_id": "R2", "duplicate_of": "R1"},
            {"item_id": "R3", "duplicate_of": None},
        ],
        "failure_patterns": [
            {
                "pattern_id": "FP-001",
                "applicable": True,
                "detected_before_expensive_work": True,
            },
            {
                "pattern_id": "FP-002",
                "applicable": False,
                "detected_before_expensive_work": False,
            },
        ],
        "queue_starvation_event_ids": ["Q1"],
        "hard_failures": [],
        "steps_to_decisive_falsification": 2,
        "coordination_overhead_units": 4,
        "plan_usage_units": 3,
    }


def telemetry(side="BASELINE", *, provenance=True):
    status = cohort()
    return {
        "schema_version": 1,
        "side": side,
        "cohort_hash": status["cohort_hash"],
        "records": [record(meta, provenance=provenance) for meta in status["cohort_case_metadata"]],
    }


def test_metrics_are_derived_from_items_not_self_reported_aggregates():
    out = build_observation_set(cohort(), telemetry(), "BASELINE")
    row = out["records"][0]
    assert row["worker_runs"] == 2
    assert row["unique_relevant_evidence"] == 2
    assert row["contradictions_found"] == 1
    assert row["research_items"] == 3
    assert row["duplicate_research_items"] == 1
    assert row["applicable_known_failure_patterns"] == 1
    assert row["failure_patterns_before_expensive_work"] == 1
    assert row["queue_starvation_events"] == 1
    assert row["source_families_covered"] == ["CODE", "OFFICIAL"]


def test_relevant_evidence_with_bad_provenance_marks_case_incomplete():
    out = build_observation_set(cohort(), telemetry(provenance=False), "BASELINE")
    assert out["records"][0]["point_in_time_and_provenance_complete"] is False


def test_irrelevant_evidence_does_not_break_provenance_completeness():
    out = build_observation_set(cohort(), telemetry(), "BASELINE")
    assert out["records"][0]["point_in_time_and_provenance_complete"] is True


def test_duplicate_evidence_identity_fails_closed():
    data = telemetry()
    data["records"][0]["evidence"][1]["evidence_id"] = "E1"
    with pytest.raises(ValueError, match="duplicate_evidence_id"):
        build_observation_set(cohort(), data, "BASELINE")


def test_predetected_non_applicable_failure_fails_closed():
    data = telemetry()
    row = data["records"][0]["failure_patterns"][1]
    row["detected_before_expensive_work"] = True
    with pytest.raises(ValueError, match="predetected_non_applicable_failure"):
        build_observation_set(cohort(), data, "BASELINE")


def test_missing_telemetry_case_fails_closed():
    data = telemetry()
    data["records"].pop()
    with pytest.raises(ValueError, match="telemetry_case_set_mismatch"):
        build_observation_set(cohort(), data, "BASELINE")


def test_telemetry_identity_drift_fails_closed():
    data = telemetry("CHALLENGER")
    data["records"][0]["candidate_id"] = "OTHER"
    with pytest.raises(ValueError, match="telemetry_identity_mismatch"):
        build_observation_set(cohort(), data, "CHALLENGER")


def test_worker_run_ids_must_be_unique_and_nonempty():
    data = telemetry()
    data["records"][0]["worker_run_ids"] = ["W1", "W1"]
    with pytest.raises(ValueError, match="worker_run_ids_invalid:.*duplicate"):
        build_observation_set(cohort(), data, "BASELINE")
