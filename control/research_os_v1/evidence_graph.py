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


def _text(value: Any) -> str:
    return str(value or "").strip()


def _validate_node(node: dict[str, Any]) -> None:
    if not isinstance(node, dict):
        raise ValueError("node_must_be_object")
    nid = _text(node.get("id"))
    if not nid:
        raise ValueError("node_id_required")
    ntype = _text(node.get("type"))
    if ntype not in VALID_NODE_TYPES:
        raise ValueError(f"invalid_node_type:{ntype}")
    if not _text(node.get("status")):
        raise ValueError(f"node_status_required:{nid}")
    if not _text(node.get("created_at")):
        raise ValueError(f"node_created_at_required:{nid}")
    if not _text(node.get("producer")):
        raise ValueError(f"node_producer_required:{nid}")


def _validate_edge_shape(edge: dict[str, Any]) -> tuple[str, str, str]:
    if not isinstance(edge, dict):
        raise ValueError("edge_must_be_object")
    source = _text(edge.get("from"))
    target = _text(edge.get("to"))
    etype = _text(edge.get("type"))
    if not source or not target:
        raise ValueError("edge_endpoints_required")
    if etype not in VALID_EDGE_TYPES:
        raise ValueError(f"invalid_edge_type:{etype}")
    if not _text(edge.get("created_at")):
        raise ValueError(f"edge_created_at_required:{source}:{target}:{etype}")
    if not _text(edge.get("producer")):
        raise ValueError(f"edge_producer_required:{source}:{target}:{etype}")
    return source, target, etype


class EvidenceGraph:
    def __init__(self, obj: dict[str, Any] | None = None):
        obj = deepcopy(obj or {"schema_version": 1, "nodes": [], "edges": []})
        if not isinstance(obj, dict):
            raise ValueError("graph_must_be_object")
        if obj.get("schema_version") != 1:
            raise ValueError("unsupported_schema_version")
        if not isinstance(obj.get("nodes"), list) or not isinstance(obj.get("edges"), list):
            raise ValueError("graph_nodes_and_edges_must_be_lists")

        self._nodes: dict[str, dict[str, Any]] = {}
        self._edges: dict[tuple[str, str, str], dict[str, Any]] = {}

        # Use the same mutation path for loading so duplicate/conflicting state
        # cannot be silently collapsed by a dict comprehension.
        for node in obj["nodes"]:
            self.add_node(node)
        for edge in obj["edges"]:
            self.add_edge(edge)

    def add_node(self, node: dict[str, Any]) -> None:
        _validate_node(node)
        nid = _text(node.get("id"))
        normalized = deepcopy(node)
        normalized["id"] = nid
        existing = self._nodes.get(nid)
        if existing is not None and existing != normalized:
            raise ValueError(f"conflicting_node:{nid}")
        self._nodes[nid] = normalized

    def add_edge(self, edge: dict[str, Any]) -> None:
        source, target, etype = _validate_edge_shape(edge)
        if source not in self._nodes or target not in self._nodes:
            raise ValueError("edge_endpoint_missing")
        key = (source, target, etype)
        normalized = deepcopy(edge)
        normalized["from"] = source
        normalized["to"] = target
        normalized["type"] = etype
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
