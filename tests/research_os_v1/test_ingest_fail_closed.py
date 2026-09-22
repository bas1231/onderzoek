import json

import pytest

from control.research_os_v1.evidence_graph import EvidenceGraph
from control.research_os_v1.shadow_cli import load_candidates, load_packets
from control.research_os_v1.shadow_cycle import build_shadow_plan


def node(node_id, node_type="evidence", status="OK"):
    row = {
        "id": node_id,
        "type": node_type,
        "status": status,
        "created_at": "2026-09-21T00:00:00Z",
        "producer": "test",
    }
    if node_type == "evidence":
        row["source_ref"] = f"raw/{node_id}.json"
        row["point_in_time_status"] = "UNKNOWN"
    return row


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


def edge(source, target, edge_type="supports"):
    return {
        "from": source,
        "to": target,
        "type": edge_type,
        "created_at": "2026-09-21T00:00:00Z",
        "producer": "test",
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


def test_evidence_node_requires_explicit_point_in_time_status():
    bad = node("e1")
    bad.pop("point_in_time_status")
    with pytest.raises(ValueError, match="evidence_point_in_time_status_required:e1"):
        EvidenceGraph({"schema_version": 1, "nodes": [bad], "edges": []})


def test_evidence_node_requires_source_ref_or_content_hash():
    bad = node("e1")
    bad.pop("source_ref")
    with pytest.raises(ValueError, match="evidence_provenance_required:e1"):
        EvidenceGraph({"schema_version": 1, "nodes": [bad], "edges": []})


def test_content_hash_alone_is_valid_evidence_provenance():
    good = node("e1")
    good.pop("source_ref")
    good["content_hash"] = "abc123"
    graph = EvidenceGraph({"schema_version": 1, "nodes": [good], "edges": []})
    assert graph.as_dict()["nodes"][0]["content_hash"] == "abc123"


def test_graph_constructor_rejects_edge_with_missing_endpoint():
    graph = {
        "schema_version": 1,
        "nodes": [node("e1")],
        "edges": [edge("e1", "missing")],
    }
    with pytest.raises(ValueError, match="edge_endpoint_missing"):
        EvidenceGraph(graph)


def test_graph_rejects_self_edge():
    graph = {
        "schema_version": 1,
        "nodes": [node("e1")],
        "edges": [edge("e1", "e1")],
    }
    with pytest.raises(ValueError, match="self_edge_not_allowed:e1"):
        EvidenceGraph(graph)


def test_graph_rejects_support_and_contradict_for_same_pair():
    graph = EvidenceGraph({
        "schema_version": 1,
        "nodes": [node("e1"), node("c1", node_type="claim")],
        "edges": [],
    })
    graph.add_edge(edge("e1", "c1", "supports"))
    with pytest.raises(ValueError, match="conflicting_edge_polarity:e1:c1"):
        graph.add_edge(edge("e1", "c1", "contradicts"))


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
