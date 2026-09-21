from __future__ import annotations

from copy import deepcopy
from typing import Any

VALID_EDGE_TYPES = {
    "supports", "contradicts", "depends_on", "tested_by",
    "invalidated_by", "supersedes", "derived_from",
}


class EvidenceGraph:
    def __init__(self, obj: dict[str, Any] | None = None):
        obj = deepcopy(obj or {"schema_version": 1, "nodes": [], "edges": []})
        if obj.get("schema_version") != 1:
            raise ValueError("unsupported_schema_version")
        self._nodes = {str(n["id"]): n for n in obj.get("nodes", [])}
        self._edges: dict[tuple[str, str, str], dict[str, Any]] = {}
        for edge in obj.get("edges", []):
            key = (str(edge["from"]), str(edge["to"]), str(edge["type"]))
            self._edges[key] = edge

    def add_node(self, node: dict[str, Any]) -> None:
        nid = str(node.get("id") or "")
        if not nid:
            raise ValueError("node_id_required")
        existing = self._nodes.get(nid)
        if existing is not None and existing != node:
            raise ValueError(f"conflicting_node:{nid}")
        self._nodes[nid] = deepcopy(node)

    def add_edge(self, edge: dict[str, Any]) -> None:
        source = str(edge.get("from") or "")
        target = str(edge.get("to") or "")
        etype = str(edge.get("type") or "")
        if source not in self._nodes or target not in self._nodes:
            raise ValueError("edge_endpoint_missing")
        if etype not in VALID_EDGE_TYPES:
            raise ValueError(f"invalid_edge_type:{etype}")
        key = (source, target, etype)
        existing = self._edges.get(key)
        if existing is not None and existing != edge:
            raise ValueError(f"conflicting_edge:{source}:{target}:{etype}")
        self._edges[key] = deepcopy(edge)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "nodes": [self._nodes[k] for k in sorted(self._nodes)],
            "edges": [self._edges[k] for k in sorted(self._edges)],
        }
