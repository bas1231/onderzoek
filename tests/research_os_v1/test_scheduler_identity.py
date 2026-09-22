import copy

import pytest

from control.research_os_v1.scheduler import schedule


def task(task_id: str) -> dict:
    return {
        "task_id": task_id,
        "worker_domain": "discovery",
        "objective": "identity test",
        "state": "READY",
        "task_shape": {
            "parallelism": "LOW",
            "dependency_shape": "SEQUENTIAL",
            "uncertainty_type": "SOURCE",
            "time_sensitivity": "LOW",
            "novelty": "INCREMENTAL",
            "decision_relevance": "LOW",
        },
        "inputs": {},
        "constraints": {
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
            "source_policy": "LOCAL_EXISTING_ONLY",
        },
        "expected_output": {
            "artifact_type": "DISCOVERY_FINDING",
            "required_fields": ["evidence"],
        },
        "scheduling": {
            "uncertainty_reduction": "LOW",
            "dependency_unlock_value": "NONE",
            "evidence_cost": "LOW",
            "model_cost": "LOW",
            "duplication_risk": "LOW",
        },
        "proposed_action": {
            "kind": "free_public_read_only_research",
            "provenance": True,
            "point_in_time": True,
        },
    }


def test_duplicate_valid_task_ids_are_control_plane_error():
    a = task("DUP")
    b = copy.deepcopy(a)
    with pytest.raises(ValueError, match="duplicate_task_id:DUP"):
        schedule([a, b])


def test_distinct_task_ids_remain_schedulable():
    out = schedule([task("A"), task("B")])
    assert set(out["selected"]) == {"A", "B"}
