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


def _required_text(value: Any, error: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(error)
    return value.strip()


def _optional_text(value: Any, error: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(error)
    text = value.strip()
    return text or None


def _string_list(packet: dict[str, Any], key: str) -> list[str]:
    value = packet.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{key}_must_be_list")
    out: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{key}_item_invalid:{index}")
        out.append(item.strip())
    return out


def _evidence_list(packet: dict[str, Any], key: str) -> list[Any]:
    value = packet.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{key}_must_be_list")
    for index, item in enumerate(value):
        if isinstance(item, str):
            if not item.strip():
                raise ValueError(f"{key}_item_invalid:{index}")
        elif not isinstance(item, dict):
            raise ValueError(f"{key}_item_invalid:{index}")
    return list(value)


def _candidate_ids(packet: dict[str, Any]) -> list[str]:
    vals: list[str] = []
    for key in ("candidate_ids", "survivors", "reproduction_candidates"):
        vals.extend(_string_list(packet, key))
    return sorted(set(vals))


def _runtime_state(status: str) -> str:
    if status in RUNNABLE:
        return "READY"
    if status in WAITING:
        return status
    return "BLOCKED"


def packet_to_task(packet: dict[str, Any], run_id: str) -> dict[str, Any] | None:
    if not isinstance(packet, dict):
        raise ValueError("packet_must_be_object")
    run = _required_text(run_id, "run_id_required")

    raw_role = packet.get("agent_id")
    if not isinstance(raw_role, str) or not raw_role.strip():
        raise ValueError("agent_id_required")
    role = raw_role.strip()
    if role not in ROLE_DOMAIN:
        return None

    raw_status = packet.get("status")
    if raw_status is None:
        status = "PENDING"
    else:
        status = _required_text(raw_status, "status_must_be_nonempty_string").upper()
    if status in TERMINAL:
        return None

    par, dep, unc, time, novelty, relevance = ROLE_SHAPE[role]
    refs = _string_list(packet, "input_refs")
    evidence = _evidence_list(packet, "routed_evidence")
    candidate_ids = _candidate_ids(packet)
    failure_pattern_ids = _string_list(packet, "failure_pattern_ids")
    state = _runtime_state(status)

    question = _optional_text(
        packet.get("next_decisive_question"),
        "next_decisive_question_must_be_string_or_null",
    )
    explicit_objective = _optional_text(
        packet.get("objective"),
        "objective_must_be_string_or_null",
    )
    objective = question or explicit_objective or (
        f"Execute {role} responsibility for run {run} using only routed evidence."
    )
    cutoff = _optional_text(
        packet.get("point_in_time_cutoff"),
        "point_in_time_cutoff_must_be_string_or_null",
    )

    return {
        "task_id": f"{run}:{role}",
        "candidate_id": candidate_ids[0] if len(candidate_ids) == 1 else None,
        "worker_domain": ROLE_DOMAIN[role],
        "legacy_role": role,
        "legacy_status": status,
        "objective": objective,
        "decisive_question": question,
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
            "failure_pattern_ids": failure_pattern_ids,
            "point_in_time_cutoff": cutoff,
        },
        "constraints": {
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
            "source_policy": "FREE_PUBLIC_ONLY",
            "blind_to_origin_reasoning": role in {
                "chief_falsifier",
                "independent_reproducer",
            },
        },
        "expected_output": {
            "artifact_type": (
                "DISCOVERY_FINDING" if ROLE_DOMAIN[role] == "discovery"
                else "FALSIFICATION" if ROLE_DOMAIN[role] == "red_team"
                else "REPRODUCTION" if ROLE_DOMAIN[role] == "independent_reproducer"
                else "DIRECTOR_DECISION" if ROLE_DOMAIN[role] == "research_director"
                else "RESEARCH_FINDING"
            ),
            "required_fields": [
                "claims", "evidence", "contradictions", "unknowns",
                "gate_effect", "economic_conclusion",
            ],
        },
        "scheduling": {
            "uncertainty_reduction": (
                "HIGH" if relevance in {"HIGH", "DECISIVE"} else "MEDIUM"
            ),
            "dependency_unlock_value": (
                "MULTIPLE"
                if role in {
                    "settlement", "microstructure", "prebuild_killer",
                    "research_director",
                }
                else "ONE"
            ),
            "evidence_cost": (
                "LOW" if role in {"scout", "recon_scout", "prebuild_killer"}
                else "MEDIUM"
            ),
            "model_cost": (
                "HIGH"
                if role in {
                    "algebra", "chief_falsifier", "independent_reproducer",
                    "research_director",
                }
                else "MEDIUM"
            ),
            "duplication_risk": (
                "MEDIUM" if role in {"scout", "recon_scout"} else "LOW"
            ),
        },
        "proposed_action": {
            "kind": "free_public_read_only_research",
            "provenance": bool(
                refs or evidence or candidate_ids or role == "research_director"
            ),
            "point_in_time": True,
        },
    }


def packets_to_tasks(packets: list[dict[str, Any]], run_id: str) -> list[dict[str, Any]]:
    if not isinstance(packets, list):
        raise ValueError("packets_must_be_list")
    out = []
    for packet in deepcopy(packets):
        task = packet_to_task(packet, run_id)
        if task is not None:
            out.append(task)
    return out
