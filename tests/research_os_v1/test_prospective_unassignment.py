import pytest

from control.research_os_v1.prospective_metrics import build_observation_set


def cohort():
    meta = {
        "case_id": "ROS1-000000000000000000000001",
        "active_hour_id": "hourly-20260922T100000+0200",
        "candidate_id": "C1",
        "task_shape": "LOW_SEQUENTIAL",
        "representative_task_id": "hourly-20260922T100000+0200:settlement",
        "legacy_role": "settlement",
    }
    return {
        "cohort_frozen": True,
        "cohort_hash": "H1",
        "cohort_case_metadata": [meta],
    }, meta


def unassigned(side="CHALLENGER"):
    status, meta = cohort()
    return status, {
        "schema_version": 1,
        "side": side,
        "cohort_hash": "H1",
        "records": [{
            **meta,
            "decision": "KEEP",
            "intentionally_unassigned": True,
            "worker_run_ids": [],
            "evidence": [],
            "research_items": [],
            "failure_patterns": [],
            "queue_starvation_event_ids": [],
            "hard_failures": [],
        }],
    }


def test_challenger_intentional_unassignment_is_explicit_zero_work_not_missing_data():
    status, telemetry = unassigned()
    out = build_observation_set(status, telemetry, "CHALLENGER")
    row = out["records"][0]
    assert row["worker_runs"] == 0
    assert row["research_items"] == 0
    assert row["unique_relevant_evidence"] == 0
    assert row["decision"] == "KEEP"


def test_baseline_cannot_claim_intentional_unassignment():
    status, telemetry = unassigned("BASELINE")
    with pytest.raises(ValueError, match="intentional_unassignment_only_challenger"):
        build_observation_set(status, telemetry, "BASELINE")


def test_unassigned_challenger_cannot_hide_research_activity():
    status, telemetry = unassigned()
    telemetry["records"][0]["research_items"] = [{"item_id": "R1", "duplicate_of": None}]
    with pytest.raises(ValueError, match="unassigned_case_has_research_activity"):
        build_observation_set(status, telemetry, "CHALLENGER")


def test_unassigned_challenger_cannot_claim_kill():
    status, telemetry = unassigned()
    telemetry["records"][0]["decision"] = "KILL"
    with pytest.raises(ValueError, match="unassigned_case_decision_must_be_keep"):
        build_observation_set(status, telemetry, "CHALLENGER")
