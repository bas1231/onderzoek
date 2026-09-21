from __future__ import annotations

from copy import deepcopy
from typing import Any

ROLE_DOMAIN = {
    "recon_scout": "discovery",
    "scout": "discovery",
    "weather_twc": "market_research",
    "behavioral": "market_research",
    "informed_flow": "market_research",
    "microstructure": "mechanics",
    "settlement": "mechanics",
    "algebra": "algebra",
    "prebuild_killer": "red_team",
    "chief_falsifier": "red_team",
    "independent_reproducer": "independent_reproducer",
    "research_director": "research_director",
}

ROLE_SHAPE = {
    "recon_scout": ("HIGH", "INDEPENDENT", "SOURCE", "HIGH", "NOVEL", "HIGH"),
    "scout": ("HIGH", "INDEPENDENT", "SOURCE", "MEDIUM", "NOVEL", "HIGH"),
    "weather_twc": ("MEDIUM", "PARTIAL", "SIGNAL", "MEDIUM", "INCREMENTAL", "HIGH"),
    "behavioral": ("MEDIUM", "PARTIAL", "SIGNAL", "LOW", "INCREMENTAL", "HIGH"),
    "informed_flow": ("MEDIUM", "PARTIAL", "SIGNAL", "MEDIUM", "INCREMENTAL", "HIGH"),
    "microstructure": ("MEDIUM", "PARTIAL", "EXECUTION", "HIGH", "INCREMENTAL", "DECISIVE"),
    "settlement": ("LOW", "SEQUENTIAL", "SEMANTIC", "HIGH", "INCREMENTAL", "DECISIVE"),
    "algebra": ("HIGH", "INDEPENDENT", "MECHANISM", "LOW", "NOVEL", "HIGH"),
    "prebuild_killer": ("HIGH", "PARTIAL", "ROBUSTNESS", "HIGH", "INCREMENTAL", "DECISIVE"),
    "chief_falsifier": ("HIGH", "PARTIAL", "ROBUSTNESS", "HIGH", "INCREMENTAL", "DECISIVE"),
    "independent_reproducer": ("LOW", "SEQUENTIAL", "ROBUSTNESS", "MEDIUM", "INCREMENTAL", "DECISIVE"),
    "research_director": ("LOW", "SEQUENTIAL", "PROCESS", "HIGH", "INCREMENTAL", "DECISIVE"),
}

RUNNABLE = {"READY"}
WAITING = {"WAITING_FOR_DATA", "WAITING_FOR_RESULT", "PARKED"}
TERMINAL = {"COMPLETED", "COMPLETE", "FAILED", "FALSIFIED", "CLOSED_NEGATIVE"}


def _candidate_ids(packet: dict[str, Any]) -> list[str]:
    vals = []
    for key in ("candidate_ids", "survivors", "reproduction_candidates"):
        raw = packet.get(key) or []
        if isinstance(raw, list):
            vals.extend(str(x) for x in raw if x)
    return sorted(set(vals))


def _runtime_state(status: str) -> str:
    if status in RUNNABLE:
        return "READY"
    if status in WAITING:
        return status
    return "BLOCKED"


def packet_to_task(packet: dict[str, Any], run_id: str) -> dict[str, Any] | None:
    role = str(packet.get("agent_id") or "")
    if role not in ROLE_DOMAIN:
        return None
    status = str(packet.get("status") or "PENDING").upper()
    if status in TERMINAL:
        return None

    par, dep, unc, time, novelty, relevance = ROLE_SHAPE[role]
    refs = list(packet.get("input_refs") or [])
    evidence = list(packet.get("routed_evidence") or [])
    candidate_ids = _candidate_ids(packet)
    state = _runtime_state(status)

    objective = str(
        packet.get("next_decisive_question")
        or packet.get("objective")
        or f"Execute {role} responsibility for run {run_id} using only routed evidence."
    )

    return {
        "task_id": f"{run_id}:{role}",
        "candidate_id": candidate_ids[0] if len(candidate_ids) == 1 else None,
        "worker_domain": ROLE_DOMAIN[role],
        "legacy_role": role,
        "legacy_status": status,
        "objective": objective,
        "decisive_question": packet.get("next_decisive_question"),
        "state": state,
        "task_shape": {
            "parallelism": par,
            "dependency_shape": dep,
            "uncertainty_type": unc,
            "time_sensitivity": time,
            "novelty": novelty,
            "decision_relevance": relevance,
        },
        "inputs": {
            "claim_ids": [],
            "evidence_refs": refs,
            "candidate_ids": candidate_ids,
            "routed_evidence_count": len(evidence),
            "failure_pattern_ids": list(packet.get("failure_pattern_ids") or []),
            "point_in_time_cutoff": packet.get("point_in_time_cutoff"),
        },
        "constraints": {
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
            "source_policy": "FREE_PUBLIC_ONLY",
            "blind_to_origin_reasoning": role in {"chief_falsifier", "independent_reproducer"},
        },
        "expected_output": {
            "artifact_type": (
                "DISCOVERY_FINDING" if ROLE_DOMAIN[role] == "discovery"
                else "FALSIFICATION" if ROLE_DOMAIN[role] == "red_team"
                else "REPRODUCTION" if ROLE_DOMAIN[role] == "independent_reproducer"
                else "DIRECTOR_DECISION" if ROLE_DOMAIN[role] == "research_director"
                else "RESEARCH_FINDING"
            ),
            "required_fields": ["claims", "evidence", "contradictions", "unknowns", "gate_effect", "economic_conclusion"],
        },
        "scheduling": {
            "uncertainty_reduction": "HIGH" if relevance in {"HIGH", "DECISIVE"} else "MEDIUM",
            "dependency_unlock_value": "MULTIPLE" if role in {"settlement", "microstructure", "prebuild_killer", "research_director"} else "ONE",
            "evidence_cost": "LOW" if role in {"scout", "recon_scout", "prebuild_killer"} else "MEDIUM",
            "model_cost": "HIGH" if role in {"algebra", "chief_falsifier", "independent_reproducer", "research_director"} else "MEDIUM",
            "duplication_risk": "MEDIUM" if role in {"scout", "recon_scout"} else "LOW",
        },
        "proposed_action": {
            "kind": "free_public_read_only_research",
            "provenance": bool(refs or evidence or candidate_ids or role == "research_director"),
            "point_in_time": True,
        },
    }


def packets_to_tasks(packets: list[dict[str, Any]], run_id: str) -> list[dict[str, Any]]:
    out = []
    for packet in deepcopy(packets):
        task = packet_to_task(packet, run_id)
        if task is not None:
            out.append(task)
    return out
