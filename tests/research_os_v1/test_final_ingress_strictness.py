import json

import pytest

from control.research_os_v1.contracts import validate_task
from control.research_os_v1.discovery_coverage import summarize as summarize_coverage
from control.research_os_v1.evidence_graph import EvidenceGraph
from control.research_os_v1.hypothesis_accounting import normalize as normalize_search_family
from control.research_os_v1.legacy_adapter import packet_to_task
from control.research_os_v1.scheduler import fanout_cap
from control.research_os_v1.shadow_cli import load_candidates, load_packets


def valid_task():
    return {
        "task_id": "T1",
        "candidate_id": None,
        "worker_domain": "discovery",
        "objective": "test",
        "decisive_question": None,
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


def test_discovery_rejects_numeric_source_identity():
    with pytest.raises(ValueError, match="source_id_must_be_string_or_null"):
        summarize_coverage(
            [{"source_id": 123, "source_family": "OFFICIAL"}],
            [],
            ["OFFICIAL"],
            ["OFFICIAL"],
        )


def test_discovery_rejects_string_boolean_retrieval_status():
    with pytest.raises(ValueError, match="retrieval_succeeded_must_be_boolean_or_null"):
        summarize_coverage(
            [{
                "source_id": "a",
                "source_family": "OFFICIAL",
                "retrieval_succeeded": "false",
            }],
            [],
            ["OFFICIAL"],
            ["OFFICIAL"],
        )


def test_unidentified_changed_item_is_not_counted_as_unique_document():
    result = summarize_coverage(
        [{"source_family": "OFFICIAL", "changed_or_new": True}],
        [],
        ["OFFICIAL"],
        ["OFFICIAL"],
    )
    assert result["changed_or_new_documents"] == 0
    assert result["changed_or_new_unidentified_items"] == 1
    assert result["changed_or_new_items_reported"] == 1
    assert result["unidentified_items_count_as_proven_unique_documents"] is False


def test_search_family_id_must_be_real_string():
    with pytest.raises(ValueError, match="search_family_id_required"):
        normalize_search_family({
            "id": 123,
            "hypotheses_examined": 1,
            "parameterizations_examined": 0,
            "post_hoc_mutations": 0,
            "untouched_evidence_remaining": True,
        })


def test_task_id_and_action_kind_are_not_stringified():
    task = valid_task()
    task["task_id"] = 123
    assert "task_id_required" in validate_task(task)

    task = valid_task()
    task["proposed_action"]["kind"] = 123
    assert "proposed_action_kind_required" in validate_task(task)


def test_fanout_cap_rejects_invalid_task_contract_directly():
    task = valid_task()
    task["task_id"] = 123
    with pytest.raises(ValueError, match="invalid_task_contract"):
        fanout_cap(task)


def test_legacy_candidate_ids_must_be_string_list():
    with pytest.raises(ValueError, match="candidate_ids_item_invalid"):
        packet_to_task(
            {
                "agent_id": "settlement",
                "status": "READY",
                "candidate_ids": [123],
                "input_refs": ["x"],
            },
            "RUN",
        )


def test_legacy_input_refs_must_be_list_not_string():
    with pytest.raises(ValueError, match="input_refs_must_be_list"):
        packet_to_task(
            {
                "agent_id": "settlement",
                "status": "READY",
                "input_refs": "x",
            },
            "RUN",
        )


def test_evidence_graph_rejects_numeric_id_and_unknown_fields():
    with pytest.raises(ValueError, match="node_id_required"):
        EvidenceGraph({
            "schema_version": 1,
            "nodes": [{
                "id": 1,
                "type": "evidence",
                "status": "OK",
                "created_at": "2026-09-22T00:00:00Z",
                "producer": "test",
            }],
            "edges": [],
        })

    with pytest.raises(ValueError, match="node_unknown_fields"):
        EvidenceGraph({
            "schema_version": 1,
            "nodes": [{
                "id": "e1",
                "type": "evidence",
                "status": "OK",
                "created_at": "2026-09-22T00:00:00Z",
                "producer": "test",
                "surprise": "not in schema",
            }],
            "edges": [],
        })


def test_shadow_cli_rejects_numeric_candidate_and_agent_ids(tmp_path):
    candidates = tmp_path / "candidates"
    candidates.mkdir()
    (candidates / "bad.json").write_text(
        json.dumps({"candidate_id": 123}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="candidate_id_missing_or_invalid"):
        load_candidates(candidates)

    packets = tmp_path / "packets"
    packets.mkdir()
    (packets / "bad.json").write_text(
        json.dumps({"agent_id": 123}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="packet_agent_id_missing_or_invalid"):
        load_packets(packets)
