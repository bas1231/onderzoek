from __future__ import annotations

from copy import deepcopy
from typing import Any

VALID_NODE_TYPES = {
    "candidate", "claim", "evidence", "assumption", "rule",
    "experiment", "failure_pattern",
}
VALID_EDGE_TYPES = {
    "supports", "contradicts", "depends_on", "tested_by",
    "invalidated_by", "supersedes", "derived_from",
}
VALID_POINT_IN_TIME = {"PASS", "FAIL", "UNKNOWN", "NOT_APPLICABLE"}
NODE_KEYS = {
    "id", "type", "status", "statement", "created_at", "observed_at",
    "retrieved_at", "point_in_time_status", "source_ref", "content_hash",
    "producer", "source_commit", "search_family_id", "metadata",
}
EDGE_KEYS = {"from", "to", "type", "created_at", "producer", "note"}


def _required_text(value: Any, error: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(error)
    return value.strip()


def _optional_text(value: Any, error: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(error)
    return value.strip()


def _normalize_node(node: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(node, dict):
        raise ValueError("node_must_be_object")
    extra = sorted(set(node) - NODE_KEYS)
    if extra:
        raise ValueError("node_unknown_fields:" + ",".join(extra))

    nid = _required_text(node.get("id"), "node_id_required")
    ntype = _required_text(node.get("type"), f"node_type_required:{nid}")
    if ntype not in VALID_NODE_TYPES:
        raise ValueError(f"invalid_node_type:{ntype}")
    status = _required_text(node.get("status"), f"node_status_required:{nid}")
    created_at = _required_text(
        node.get("created_at"),
        f"node_created_at_required:{nid}",
    )
    producer = _required_text(
        node.get("producer"),
        f"node_producer_required:{nid}",
    )

    normalized = deepcopy(node)
    normalized.update({
        "id": nid,
        "type": ntype,
        "status": status,
        "created_at": created_at,
        "producer": producer,
    })

    for key in (
        "statement", "observed_at", "retrieved_at", "source_ref",
        "content_hash", "source_commit", "search_family_id",
    ):
        if key in node:
            normalized[key] = _optional_text(
                node.get(key),
                f"node_{key}_must_be_string_or_null:{nid}",
            )

    if "point_in_time_status" in node:
        value = node.get("point_in_time_status")
        if value not in VALID_POINT_IN_TIME:
            raise ValueError(f"invalid_point_in_time_status:{nid}")
    if "metadata" in node and not isinstance(node.get("metadata"), dict):
        raise ValueError(f"node_metadata_must_be_object:{nid}")

    return normalized


def _normalize_edge(edge: dict[str, Any]) -> tuple[tuple[str, str, str], dict[str, Any]]:
    if not isinstance(edge, dict):
        raise ValueError("edge_must_be_object")
    extra = sorted(set(edge) - EDGE_KEYS)
    if extra:
        raise ValueError("edge_unknown_fields:" + ",".join(extra))

    source = _required_text(edge.get("from"), "edge_source_required")
    target = _required_text(edge.get("to"), "edge_target_required")
    etype = _required_text(edge.get("type"), "edge_type_required")
    if etype not in VALID_EDGE_TYPES:
        raise ValueError(f"invalid_edge_type:{etype}")
    created_at = _required_text(
        edge.get("created_at"),
        f"edge_created_at_required:{source}:{target}:{etype}",
    )
    producer = _required_text(
        edge.get("producer"),
        f"edge_producer_required:{source}:{target}:{etype}",
    )

    normalized = deepcopy(edge)
    normalized.update({
        "from": source,
        "to": target,
        "type": etype,
        "created_at": created_at,
        "producer": producer,
    })
    if "note" in edge:
        normalized["note"] = _optional_text(
            edge.get("note"),
            f"edge_note_must_be_string_or_null:{source}:{target}:{etype}",
        )
    return (source, target, etype), normalized


class EvidenceGraph:
    def __init__(self, obj: dict[str, Any] | None = None):
        obj = deepcopy(obj or {"schema_version": 1, "nodes": [], "edges": []})
        if not isinstance(obj, dict):
            raise ValueError("graph_must_be_object")
        if set(obj) - {"schema_version", "nodes", "edges"}:
            raise ValueError("graph_unknown_fields")
        if (
            obj.get("schema_version") != 1
            or isinstance(obj.get("schema_version"), bool)
        ):
            raise ValueError("unsupported_schema_version")
        if not isinstance(obj.get("nodes"), list) or not isinstance(obj.get("edges"), list):
            raise ValueError("graph_nodes_and_edges_must_be_lists")

        self._nodes: dict[str, dict[str, Any]] = {}
        self._edges: dict[tuple[str, str, str], dict[str, Any]] = {}

        for node in obj["nodes"]:
            self.add_node(node)
        for edge in obj["edges"]:
            self.add_edge(edge)

    def add_node(self, node: dict[str, Any]) -> None:
        normalized = _normalize_node(node)
        nid = normalized["id"]
        existing = self._nodes.get(nid)
        if existing is not None and existing != normalized:
            raise ValueError(f"conflicting_node:{nid}")
        self._nodes[nid] = normalized

    def add_edge(self, edge: dict[str, Any]) -> None:
        key, normalized = _normalize_edge(edge)
        source, target, etype = key
        if source not in self._nodes or target not in self._nodes:
            raise ValueError("edge_endpoint_missing")
        existing = self._edges.get(key)
        if existing is not None and existing != normalized:
            raise ValueError(f"conflicting_edge:{source}:{target}:{etype}")
        self._edges[key] = normalized

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "nodes": [deepcopy(self._nodes[k]) for k in sorted(self._nodes)],
            "edges": [deepcopy(self._edges[k]) for k in sorted(self._edges)],
        }
