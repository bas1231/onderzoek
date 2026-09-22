import json

import pytest

from control.research_os_v1.prospective_collector import safe_cycle_filename
from control.research_os_v1.prospective_materialize import materialize_observation_inputs


def cohort_status():
    rows = [
        {
            "case_id": "ROS1-000000000000000000000001",
            "active_hour_id": "hourly-20260922T100000+0200",
            "candidate_id": "C1",
            "task_shape": "LOW_SEQUENTIAL",
            "representative_task_id": "hourly-20260922T100000+0200:settlement",
            "legacy_role": "settlement",
        },
        {
            "case_id": "ROS1-000000000000000000000002",
            "active_hour_id": "hourly-20260922T110000+0200",
            "candidate_id": "C2",
            "task_shape": "HIGH_INDEPENDENT",
            "representative_task_id": "hourly-20260922T110000+0200:scout",
            "legacy_role": "scout",
        },
    ]
    return {
        "cohort_frozen": True,
        "cohort_hash": "H1",
        "cohort_case_metadata": rows,
    }


def _write_raw(root, side, hour, records):
    path = root / "raw_telemetry" / side.lower() / safe_cycle_filename(hour)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "schema_version": 1,
        "side": side,
        "run_id": hour,
        "source_commit": "abc",
        "request_sha256": "req",
        "records": records,
        "economic_conclusion": "NO_PROVEN_EDGE",
    }), encoding="utf-8")


def test_materializes_only_exact_frozen_cohort_cases(tmp_path):
    status = cohort_status()
    for meta in status["cohort_case_metadata"]:
        for side in ("BASELINE", "CHALLENGER"):
            _write_raw(tmp_path, side, meta["active_hour_id"], [{**meta, "decision": "KEEP"}])
    baseline, challenger = materialize_observation_inputs(tmp_path, status)
    assert baseline["cohort_hash"] == "H1"
    assert challenger["cohort_hash"] == "H1"
    assert [r["case_id"] for r in baseline["records"]] == [
        "ROS1-000000000000000000000001",
        "ROS1-000000000000000000000002",
    ]
    assert [r["case_id"] for r in challenger["records"]] == [
        "ROS1-000000000000000000000001",
        "ROS1-000000000000000000000002",
    ]


def test_missing_raw_cycle_blocks_materialization(tmp_path):
    status = cohort_status()
    first = status["cohort_case_metadata"][0]
    for side in ("BASELINE", "CHALLENGER"):
        _write_raw(tmp_path, side, first["active_hour_id"], [first])
    with pytest.raises(ValueError, match="raw_telemetry_missing"):
        materialize_observation_inputs(tmp_path, status)


def test_duplicate_case_in_raw_cycle_fails_closed(tmp_path):
    status = cohort_status()
    for meta in status["cohort_case_metadata"]:
        records = [meta, dict(meta)] if meta["candidate_id"] == "C1" else [meta]
        for side in ("BASELINE", "CHALLENGER"):
            _write_raw(tmp_path, side, meta["active_hour_id"], records)
    with pytest.raises(ValueError, match="raw_case_match_count:BASELINE"):
        materialize_observation_inputs(tmp_path, status)


def test_raw_run_id_mismatch_fails_closed(tmp_path):
    status = cohort_status()
    meta = status["cohort_case_metadata"][0]
    path = tmp_path / "raw_telemetry" / "baseline" / safe_cycle_filename(meta["active_hour_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "schema_version": 1,
        "side": "BASELINE",
        "run_id": "hourly-OTHER",
        "records": [meta],
        "economic_conclusion": "NO_PROVEN_EDGE",
    }), encoding="utf-8")
    # Challenger file exists so the failure is specifically the baseline run-id.
    _write_raw(tmp_path, "CHALLENGER", meta["active_hour_id"], [meta])
    with pytest.raises(ValueError, match="raw_telemetry_run_id_mismatch"):
        materialize_observation_inputs(tmp_path, {
            **status,
            "cohort_case_metadata": [meta],
        })
