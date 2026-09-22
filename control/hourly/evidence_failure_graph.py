from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib
import json


ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / "knowledge/research_os"
EVIDENCE_PATH = STORE / "evidence_graph.json"
FAILURE_PATH = STORE / "failure_graph.json"

FAILURE_PATTERNS = {
    "FP-001": "SAME_TITLE_NOT_SAME_CONTRACT",
    "FP-002": "SETTLEMENT_SOURCE_MISMATCH",
    "FP-003": "SETTLEMENT_TRANSFORMATION_MISMATCH",
    "FP-004": "UI_OR_MIDPOINT_NOT_EXECUTABLE",
    "FP-005": "STALE_MIRROR_OR_CACHE",
    "FP-006": "THEORETICAL_IDENTITY_NOT_ECONOMIC_EDGE",
    "FP-007": "GROSS_EDGE_DIES_AFTER_FRICTION",
    "FP-008": "PARTIAL_FILL_OR_LEGGING_RISK",
    "FP-009": "QUEUE_CANCELLATION_AS_FILL",
    "FP-010": "SCORE_OR_STATE_NOT_FINAL",
    "FP-011": "HIDDEN_EXCEPTION_CLASS",
    "FP-012": "DISCRETE_DOMAIN_ASSUMPTION",
    "FP-013": "COLLATERAL_RETURN_NOT_WEALTH",
    "FP-014": "CLOSE_BEFORE_INFORMATION",
    "FP-015": "LOOKAHEAD_OR_REVISION_LEAKAGE",
    "FP-016": "LEGACY_RECONSTRUCTION",
    "FP-017": "AUTH_OR_VISIBILITY_GAP",
    "FP-018": "REST_SAMPLING_MISSES_FAST_REPRICE",
    "FP-019": "WS_SEQUENCE_GAP",
    "FP-020": "DUPLICATE_TRADE_OR_WINDOW_COUNT",
    "FP-021": "MULTIPLE_TESTING_FALSE_DISCOVERY",
    "FP-022": "POST_HOC_GATE_RELAXATION",
    "FP-023": "SHARED_UPSTREAM_SOURCE",
    "FP-024": "INACTIVE_REWARD_OR_FEE_REGIME",
    "FP-025": "VARIABLE_EXTERNAL_YIELD",
    "FP-026": "ONCHAIN_OR_ASYNC_EXECUTION_FAILURE",
    "FP-027": "ADVERSE_SELECTION_IGNORED",
    "FP-028": "CAPACITY_OR_DEPTH_COLLAPSE",
    "FP-029": "TIME_UNIT_TIMEZONE_MISMATCH",
    "FP-030": "CORRELATED_EVIDENCE_DOUBLE_COUNT",
    "FP-031": "DISCOVERY_SOURCE_OVERLAP",
    "FP-032": "CANDIDATE_STATE_SPLIT_BRAIN",
    "FP-033": "STALE_GIT_OR_CONCURRENT_WRITE",
    "FP-034": "PROMPT_INJECTION_FROM_SOURCE",
    "FP-035": "DIRECTOR_CONFIRMATION_BIAS",
    "FP-036": "ZOMBIE_CANDIDATE",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def stable_id(prefix: str, payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return prefix + "-" + hashlib.sha256(encoded).hexdigest()[:20]


def empty_evidence_graph() -> dict[str, Any]:
    return {
        "schema": "PVA_EVIDENCE_GRAPH_V1",
        "updated_at": None,
        "nodes": {},
        "edges": {},
        "run_index": {},
        "guardrails": {
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
            "openai_api": False,
        },
    }


def empty_failure_graph() -> dict[str, Any]:
    return {
        "schema": "PVA_FAILURE_GRAPH_V1",
        "updated_at": None,
        "patterns": {
            pid: {
                "pattern_id": pid,
                "name": name,
                "encounters": [],
                "candidate_ids": [],
            }
            for pid, name in FAILURE_PATTERNS.items()
        },
        "candidate_failures": {},
        "negative_results": {},
        "guardrails": {
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
            "openai_api": False,
        },
    }


def _upsert_node(graph: dict[str, Any], node_id: str, payload: dict[str, Any]) -> None:
    nodes = graph.setdefault("nodes", {})
    current = nodes.get(node_id)
    if isinstance(current, dict):
        merged = dict(current)
        merged.update({k: v for k, v in payload.items() if v is not None})
        nodes[node_id] = merged
    else:
        nodes[node_id] = payload


def _upsert_edge(graph: dict[str, Any], edge: dict[str, Any]) -> str:
    edge_id = stable_id("edge", edge)
    graph.setdefault("edges", {})[edge_id] = edge
    return edge_id


def record_cycle_inputs(
    run_id: str,
    routing: dict[str, Any],
    candidate_routing: list[dict[str, Any]],
) -> dict[str, Any]:
    graph = load_json(EVIDENCE_PATH, empty_evidence_graph())
    run_edges: list[str] = []

    for capability, routed in sorted(routing.items()):
        if not isinstance(routed, dict):
            continue
        for item in routed.get("evidence", []):
            if not isinstance(item, dict):
                continue
            evidence_payload = {
                "source_id": item.get("source_id"),
                "document_sha256": item.get("document_sha256"),
                "retrieved_at": item.get("retrieved_at"),
                "term": item.get("term"),
                "capability": capability,
            }
            eid = stable_id("evidence", evidence_payload)
            _upsert_node(graph, eid, {
                "node_type": "evidence",
                **evidence_payload,
                "first_seen_run": run_id,
            })
            run_edges.append(_upsert_edge(graph, {
                "from": f"run:{run_id}",
                "to": eid,
                "type": "OBSERVED_EVIDENCE",
                "capability": capability,
            }))

    for assignment in candidate_routing:
        if not isinstance(assignment, dict):
            continue
        cid = str(assignment.get("candidate_id") or "")
        if not cid:
            continue
        candidate_node = f"candidate:{cid}"
        _upsert_node(graph, candidate_node, {
            "node_type": "candidate",
            "candidate_id": cid,
            "last_seen_run": run_id,
        })
        run_edges.append(_upsert_edge(graph, {
            "from": candidate_node,
            "to": f"domain:{assignment.get('role')}",
            "type": "ROUTED_TO_DOMAIN",
            "capability": assignment.get("capability"),
            "run_id": run_id,
            "reasons": assignment.get("reasons", []),
        }))

    graph.setdefault("run_index", {})[run_id] = sorted(set(run_edges))
    graph["updated_at"] = now_iso()
    save_json(EVIDENCE_PATH, graph)
    return {
        "evidence_graph_ref": str(EVIDENCE_PATH.relative_to(ROOT)),
        "run_edge_count": len(set(run_edges)),
    }


def _extract_failure_pattern_ids(value: Any) -> list[str]:
    text = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).upper()
    out = []
    for pid, name in FAILURE_PATTERNS.items():
        if pid in text or name in text:
            out.append(pid)
    return sorted(set(out))


def record_ai_response(run_id: str, response: dict[str, Any]) -> dict[str, Any]:
    evidence = load_json(EVIDENCE_PATH, empty_evidence_graph())
    failure = load_json(FAILURE_PATH, empty_failure_graph())

    for result in response.get("role_results", []):
        if not isinstance(result, dict):
            continue
        role = str(result.get("agent_id") or "")
        finding = result.get("finding")
        candidate_ids = [str(x) for x in result.get("candidate_ids", []) if x]
        refs = [str(x) for x in result.get("evidence_refs", []) if x]
        capability_results = result.get("capability_results", {})

        for cid in candidate_ids:
            candidate_node = f"candidate:{cid}"
            _upsert_node(evidence, candidate_node, {
                "node_type": "candidate",
                "candidate_id": cid,
                "last_seen_run": run_id,
            })
            if finding:
                claim_payload = {
                    "run_id": run_id,
                    "agent_id": role,
                    "candidate_id": cid,
                    "finding": finding,
                }
                claim_id = stable_id("claim", claim_payload)
                _upsert_node(evidence, claim_id, {
                    "node_type": "claim",
                    **claim_payload,
                })
                _upsert_edge(evidence, {
                    "from": candidate_node,
                    "to": claim_id,
                    "type": "HAS_CLAIM",
                    "run_id": run_id,
                })
                for ref in refs:
                    ref_node = stable_id("ref", {"ref": ref})
                    _upsert_node(evidence, ref_node, {
                        "node_type": "evidence_ref",
                        "ref": ref,
                    })
                    _upsert_edge(evidence, {
                        "from": claim_id,
                        "to": ref_node,
                        "type": "SUPPORTED_BY",
                        "run_id": run_id,
                    })

        for pid in _extract_failure_pattern_ids({
            "finding": finding,
            "capability_results": capability_results,
            "validation_results": result.get("validation_results", []),
        }):
            pattern = failure.setdefault("patterns", {}).setdefault(pid, {
                "pattern_id": pid,
                "name": FAILURE_PATTERNS.get(pid, pid),
                "encounters": [],
                "candidate_ids": [],
            })
            encounter = {
                "run_id": run_id,
                "agent_id": role,
                "candidate_ids": candidate_ids,
                "status": result.get("status"),
            }
            enc_id = stable_id("encounter", {"pattern_id": pid, **encounter})
            if enc_id not in {x.get("encounter_id") for x in pattern.get("encounters", []) if isinstance(x, dict)}:
                pattern.setdefault("encounters", []).append({"encounter_id": enc_id, **encounter})
            ids = {str(x) for x in pattern.get("candidate_ids", []) if x}
            ids.update(candidate_ids)
            pattern["candidate_ids"] = sorted(ids)
            for cid in candidate_ids:
                rows = failure.setdefault("candidate_failures", {}).setdefault(cid, [])
                if pid not in rows:
                    rows.append(pid)
                    rows.sort()

    for decision in response.get("candidate_decisions", []):
        if not isinstance(decision, dict):
            continue
        cid = str(decision.get("candidate_id") or "")
        status = str(decision.get("queue_status") or "")
        reason = str(decision.get("reason") or "")
        if not cid:
            continue
        _upsert_edge(evidence, {
            "from": f"candidate:{cid}",
            "to": f"state:{status}",
            "type": "LIFECYCLE_DECISION",
            "run_id": run_id,
            "reason": reason,
        })
        if status in {"PARKED", "CLOSED_NEGATIVE", "NEEDS_REVISION"}:
            neg_id = stable_id("negative", {
                "run_id": run_id,
                "candidate_id": cid,
                "status": status,
                "reason": reason,
            })
            failure.setdefault("negative_results", {})[neg_id] = {
                "negative_id": neg_id,
                "run_id": run_id,
                "candidate_id": cid,
                "status": status,
                "reason": reason,
                "resurrection_condition": decision.get("resurrection_condition"),
            }

    evidence["updated_at"] = now_iso()
    failure["updated_at"] = now_iso()
    save_json(EVIDENCE_PATH, evidence)
    save_json(FAILURE_PATH, failure)
    return {
        "evidence_graph_ref": str(EVIDENCE_PATH.relative_to(ROOT)),
        "failure_graph_ref": str(FAILURE_PATH.relative_to(ROOT)),
        "failure_pattern_count": len(failure.get("patterns", {})),
    }
