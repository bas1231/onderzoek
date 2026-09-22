#!/usr/bin/env python3
"""Offline schema-shape validator for Research OS V1.

This checks critical invariants shared by the Python adapters and their JSON
schemas. It performs no network calls and no runtime mutation.
"""
from __future__ import annotations

import json
from pathlib import Path

from .candidate_view import ALLOWED_PRIORITY, ALLOWED_QUEUE_STATUS

BASE = Path(__file__).resolve().parent


def load(name: str) -> dict:
    path = BASE / name
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"schema_not_object:{name}")
    return obj


def has_string_or_object_items(prop: dict) -> bool:
    items = prop.get("items") if isinstance(prop, dict) else None
    variants = items.get("anyOf") if isinstance(items, dict) else None
    if not isinstance(variants, list):
        return False
    types = {v.get("type") for v in variants if isinstance(v, dict)}
    return {"string", "object"}.issubset(types)


def evidence_provenance_guard_present(node_schema: dict) -> bool:
    for rule in node_schema.get("allOf") or []:
        if not isinstance(rule, dict):
            continue
        if_block = rule.get("if") or {}
        type_const = (
            if_block.get("properties", {})
            .get("type", {})
            .get("const")
        )
        then = rule.get("then") or {}
        required = set(then.get("required") or [])
        any_of = then.get("anyOf") or []
        required_alternatives = {
            tuple(option.get("required") or [])
            for option in any_of
            if isinstance(option, dict)
        }
        if (
            type_const == "evidence"
            and "point_in_time_status" in required
            and ("source_ref",) in required_alternatives
            and ("content_hash",) in required_alternatives
        ):
            return True
    return False


def main() -> int:
    errors: list[str] = []
    canonical = load("canonical_candidate.schema.json")
    worker = load("worker_contract.schema.json")
    graph = load("evidence_graph.schema.json")

    canonical_props = canonical.get("properties") or {}
    canonical_required = set(canonical.get("required") or [])
    expected_canonical = {
        "candidate_id", "version", "hypothesis", "mechanism", "phase",
        "queue_status", "economic_status", "priority", "claims", "assumptions",
        "supporting_evidence", "contradictory_evidence",
        "known_failure_patterns", "kill_conditions", "resurrection_conditions",
        "required_gates", "search_family", "next_decisive_question",
        "dependencies", "blockers", "point_in_time_cutoff", "source_commit",
        "updated_at",
    }
    if canonical_required != expected_canonical:
        errors.append("CANONICAL_REQUIRED_FIELDS_DRIFT")
    if canonical.get("additionalProperties") is not False:
        errors.append("CANONICAL_TOP_LEVEL_NOT_CLOSED")
    for key in ("claims", "assumptions", "supporting_evidence", "contradictory_evidence"):
        if not has_string_or_object_items(canonical_props.get(key) or {}):
            errors.append(f"CANONICAL_{key.upper()}_DOES_NOT_ALLOW_STRING_OR_OBJECT")
    gates = canonical_props.get("required_gates") or {}
    allowed_gate_states = set((gates.get("additionalProperties") or {}).get("enum") or [])
    if allowed_gate_states != {"PASS", "FAIL", "PENDING", "UNKNOWN", "NOT_APPLICABLE"}:
        errors.append("CANONICAL_GATE_STATES_DRIFT")

    schema_queue_status = set((canonical_props.get("queue_status") or {}).get("enum") or [])
    if schema_queue_status != ALLOWED_QUEUE_STATUS:
        errors.append("CANONICAL_QUEUE_STATUS_ENUM_DRIFT")
    schema_priority = set((canonical_props.get("priority") or {}).get("enum") or [])
    if schema_priority != ALLOWED_PRIORITY:
        errors.append("CANONICAL_PRIORITY_ENUM_DRIFT")

    worker_props = worker.get("properties") or {}
    worker_required = set(worker.get("required") or [])
    for key in (
        "task_id", "worker_domain", "objective", "state", "task_shape", "inputs",
        "constraints", "expected_output", "scheduling", "proposed_action",
    ):
        if key not in worker_required:
            errors.append(f"WORKER_REQUIRED_FIELD_MISSING:{key}")
    task_id = worker_props.get("task_id") or {}
    if task_id.get("type") != "string" or task_id.get("minLength") != 1:
        errors.append("WORKER_TASK_ID_NOT_STRICT_STRING")
    action_kind = (
        worker_props.get("proposed_action", {})
        .get("properties", {})
        .get("kind", {})
    )
    if action_kind.get("type") != "string" or action_kind.get("minLength") != 1:
        errors.append("WORKER_ACTION_KIND_NOT_STRICT_STRING")
    for flag in ("live_trading", "paid_actions", "wallet_actions"):
        node = (
            worker_props.get("constraints", {})
            .get("properties", {})
            .get(flag, {})
        )
        if node.get("const") is not False:
            errors.append(f"WORKER_SAFETY_FLAG_NOT_FALSE:{flag}")

    if graph.get("additionalProperties") is not False:
        errors.append("GRAPH_TOP_LEVEL_NOT_CLOSED")
    node_schema = (
        graph.get("properties", {})
        .get("nodes", {})
        .get("items", {})
    )
    edge_schema = (
        graph.get("properties", {})
        .get("edges", {})
        .get("items", {})
    )
    if node_schema.get("additionalProperties") is not False:
        errors.append("GRAPH_NODE_SCHEMA_NOT_CLOSED")
    if edge_schema.get("additionalProperties") is not False:
        errors.append("GRAPH_EDGE_SCHEMA_NOT_CLOSED")
    for key in ("id", "type", "status", "created_at", "producer"):
        if key not in set(node_schema.get("required") or []):
            errors.append(f"GRAPH_NODE_REQUIRED_FIELD_MISSING:{key}")
    if not evidence_provenance_guard_present(node_schema):
        errors.append("GRAPH_EVIDENCE_PROVENANCE_GUARD_MISSING")
    for key in ("from", "to", "type", "created_at", "producer"):
        if key not in set(edge_schema.get("required") or []):
            errors.append(f"GRAPH_EDGE_REQUIRED_FIELD_MISSING:{key}")

    output = {
        "validator": "RESEARCH_OS_V1_SCHEMA_ALIGNMENT",
        "status": "PASS" if not errors else "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "network_calls": False,
        "runtime_mutation": False,
        "economic_conclusion": "NO_PROVEN_EDGE",
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
