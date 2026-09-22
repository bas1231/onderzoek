import pytest

from control.research_os_v1.prospective_pairing import (
    build_paired_benchmark,
    normalize_observation_set,
)


def cohort_status():
    metadata = []
    resolutions = []
    for i in range(20):
        case_id = f"ROS1-{i:024x}"
        hour = f"hourly-202609{10 + i // 2:02d}T120000+0200"
        shape = "LOW_SEQUENTIAL" if i % 2 == 0 else "HIGH_INDEPENDENT"
        metadata.append({
            "case_id": case_id,
            "active_hour_id": hour,
            "candidate_id": f"C-{i:02d}",
            "task_shape": shape,
            "representative_task_id": f"{hour}:role-{i:02d}",
            "legacy_role": "settlement" if i % 2 == 0 else "scout",
        })
        resolutions.append({
            "case_id": case_id,
            "ground_truth_class": "SURVIVOR" if i == 0 else "DECISIVE_NEGATIVE",
            "status": "RESOLVED",
            "basis_refs": [f"basis/{i}.json"],
        })
    return {
        "schema_version": 1,
        "status": "READY_FOR_PAIRED_OBSERVATIONS",
        "cohort_frozen": True,
        "replacement_benchmark_ready": True,
        "cohort_hash": "cohort-hash-1",
        "cohort_case_metadata": metadata,
        "cohort_case_ids": [row["case_id"] for row in metadata],
        "resolutions": resolutions,
    }


def observation_set(side="BASELINE", *, better=False):
    status = cohort_status()
    records = []
    for i, meta in enumerate(status["cohort_case_metadata"]):
        survivor = i == 0
        records.append({
            **meta,
            # This field is intentionally ignored by the builder. Ground truth
            # must come from the frozen cohort resolver only.
            "ground_truth_class": "DECISIVE_NEGATIVE" if survivor else "SURVIVOR",
            "decision": "KEEP" if survivor else "KILL",
            "worker_runs": 2,
            "unique_relevant_evidence": 3 if better else 2,
            "duplicate_research_items": 0 if better else 1,
            "research_items": 3,
            "contradictions_found": 1,
            "failure_patterns_before_expensive_work": 1,
            "applicable_known_failure_patterns": 1,
            "queue_starvation_events": 0,
            "steps_to_decisive_falsification": None if survivor else 2,
            "point_in_time_and_provenance_complete": True,
            "source_families_covered": ["OFFICIAL", "CODE"],
            "hard_failures": [],
        })
    return {
        "schema_version": 1,
        "side": side,
        "cohort_hash": status["cohort_hash"],
        "records": records,
    }


def test_exact_pairing_can_meet_scientific_gate_without_authorizing_runtime():
    out = build_paired_benchmark(
        cohort_status(), observation_set("BASELINE"), observation_set("CHALLENGER", better=True)
    )
    assert out["status"] == "SCIENTIFIC_REPLACEMENT_GATE_MET"
    assert out["replacement_check"]["scientific_replacement_gate_met"] is True
    assert set(out["replacement_check"]["strict_improvements"]) >= {"M1", "M2"}
    assert out["automatic_runtime_replacement_authorized"] is False
    assert out["requires_human_integration_decision"] is True
    assert out["economic_conclusion"] == "NO_PROVEN_EDGE"


def test_observation_cannot_relabel_ground_truth():
    rows = normalize_observation_set(
        cohort_status(), observation_set("BASELINE"), "BASELINE"
    )
    assert rows[0]["ground_truth_class"] == "SURVIVOR"
    assert all(row["ground_truth_class"] == "DECISIVE_NEGATIVE" for row in rows[1:])


def test_missing_case_fails_closed():
    obs = observation_set("BASELINE")
    obs["records"].pop()
    with pytest.raises(ValueError, match="observation_case_set_mismatch"):
        normalize_observation_set(cohort_status(), obs, "BASELINE")


def test_extra_case_fails_closed():
    obs = observation_set("BASELINE")
    extra = dict(obs["records"][0])
    extra["case_id"] = "ROS1-ffffffffffffffffffffffff"
    obs["records"].append(extra)
    with pytest.raises(ValueError, match="observation_unknown_case"):
        normalize_observation_set(cohort_status(), obs, "BASELINE")


def test_identity_drift_fails_closed():
    obs = observation_set("CHALLENGER")
    obs["records"][0]["task_shape"] = "MEDIUM_PARTIAL"
    with pytest.raises(ValueError, match="identity_mismatch:CHALLENGER"):
        normalize_observation_set(cohort_status(), obs, "CHALLENGER")


def test_cohort_hash_drift_fails_closed():
    obs = observation_set("BASELINE")
    obs["cohort_hash"] = "other-cohort"
    with pytest.raises(ValueError, match="observation_cohort_hash_mismatch"):
        normalize_observation_set(cohort_status(), obs, "BASELINE")


def test_unresolved_cohort_cannot_be_paired():
    status = cohort_status()
    status["replacement_benchmark_ready"] = False
    status["status"] = "RESOLVING"
    with pytest.raises(ValueError, match="cohort_not_ready_for_paired_observations"):
        normalize_observation_set(status, observation_set("BASELINE"), "BASELINE")


def test_falsified_negative_requires_falsification_steps():
    obs = observation_set("BASELINE")
    obs["records"][1]["steps_to_decisive_falsification"] = None
    with pytest.raises(ValueError, match="steps_required_for_falsified_negative"):
        normalize_observation_set(cohort_status(), obs, "BASELINE")


def test_unfalsified_negative_is_counted_by_m6_without_inventing_steps():
    obs = observation_set("CHALLENGER")
    obs["records"][1]["decision"] = "KEEP"
    obs["records"][1]["steps_to_decisive_falsification"] = None
    rows = normalize_observation_set(cohort_status(), obs, "CHALLENGER")
    assert rows[1]["ground_truth_class"] == "DECISIVE_NEGATIVE"
    assert rows[1]["decision"] == "KEEP"
    assert "steps_to_decisive_falsification" not in rows[1]


def test_invalid_decision_fails_closed():
    obs = observation_set("CHALLENGER")
    obs["records"][0]["decision"] = "MAYBE"
    with pytest.raises(ValueError, match="invalid_decision"):
        normalize_observation_set(cohort_status(), obs, "CHALLENGER")
