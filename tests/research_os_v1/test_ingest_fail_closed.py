import json

import pytest

from control.research_os_v1.evidence_graph import EvidenceGraph
from control.research_os_v1.shadow_cli import load_candidates, load_packets
from control.research_os_v1.shadow_cycle import build_shadow_plan


def node(node_id, node_type="evidence", status="OK"):
    return {
        "id": node_id,
        "type": node_type,
        "status": status,
        "created_at": "2026-09-21T00:00:00Z",
        "producer": "test",
    }


def task(task_id="T1"):
    return {
        "task_id": task_id,
        "worker_domain": "discovery",
        "objective": "test",
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


def test_graph_constructor_rejects_conflicting_duplicate_node():
    graph = {
        "schema_version": 1,
        "nodes": [node("e1"), node("e1", status="DIFFERENT")],
        "edges": [],
    }
    with pytest.raises(ValueError, match="conflicting_node:e1"):
        EvidenceGraph(graph)


def test_graph_constructor_rejects_invalid_node_type():
    graph = {
        "schema_version": 1,
        "nodes": [node("e1", node_type="magic")],
        "edges": [],
    }
    with pytest.raises(ValueError, match="invalid_node_type"):
        EvidenceGraph(graph)


def test_graph_constructor_rejects_edge_with_missing_endpoint():
    graph = {
        "schema_version": 1,
        "nodes": [node("e1")],
        "edges": [{
            "from": "e1",
            "to": "missing",
            "type": "supports",
            "created_at": "2026-09-21T00:00:00Z",
            "producer": "test",
        }],
    }
    with pytest.raises(ValueError, match="edge_endpoint_missing"):
        EvidenceGraph(graph)


def test_candidate_loader_rejects_duplicate_identity(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps({"candidate_id": "C1"}))
    (tmp_path / "b.json").write_text(json.dumps({"candidate_id": "C1"}))
    with pytest.raises(ValueError, match="duplicate_candidate_id:C1"):
        load_candidates(tmp_path)


def test_packet_loader_rejects_duplicate_agent_identity(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps({"agent_id": "settlement"}))
    (tmp_path / "b.json").write_text(json.dumps({"agent_id": "settlement"}))
    with pytest.raises(ValueError, match="duplicate_packet_agent_id:settlement"):
        load_packets(tmp_path)


def test_candidate_loader_rejects_corrupt_json(tmp_path):
    (tmp_path / "bad.json").write_text("{not json")
    with pytest.raises(ValueError, match="invalid_json"):
        load_candidates(tmp_path)


def test_shadow_cycle_rejects_duplicate_candidate_ids_directly():
    candidates = [
        {"candidate_id": "C1", "hypothesis": "a"},
        {"candidate_id": "C1", "hypothesis": "b"},
    ]
    with pytest.raises(ValueError, match="duplicate_candidate_id:C1"):
        build_shadow_plan(candidates, [task()], source_commit="abc")


def test_shadow_cycle_rejects_duplicate_task_ids_directly():
    with pytest.raises(ValueError, match="duplicate_task_id:T1"):
        build_shadow_plan([], [task("T1"), task("T1")], source_commit="abc")
