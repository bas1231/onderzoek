from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import time

try:
    from control.hourly.candidate_worker_routing import (
        hydrate_candidate_routes,
    )
except ModuleNotFoundError:  # direct-script/importlib execution fallback
    from candidate_worker_routing import hydrate_candidate_routes


ROOT = Path.cwd()

PACKETS = ROOT / "knowledge/runs/agent_packets"

PRIMARY_ROLES = {
    "recon_scout",
    "scout",
    "algebra",
    "settlement",
    "microstructure",
    "behavioral",
    "informed_flow",
    "weather_twc",
}

CONTROL_ROLES = {
    "prebuild_killer",
    "chief_falsifier",
    "independent_reproducer",
    "research_director",
}

VALID_STATES = {
    "PENDING",
    "READY",
    "RUNNING",
    "NO_EVIDENCE",
    "WAITING_FOR_DATA",
    "WAITING_FOR_RESULT",
    "RESULT_READY",
    "COMPLETED",
    "FAILED",
    "FALSIFIED",
    "PARKED",
}

PRIORITIES = {
    "P0": 0,
    "P1": 1,
    "P2": 2,
    "P3": 3,
}


@dataclass(frozen=True)
class Decision:
    state: str
    priority: str
    reason: str


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, obj: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(obj, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def has_evidence(packet: dict[str, Any]) -> bool:
    return bool(
        packet.get("input_refs")
        or packet.get("notes")
        or packet.get("routed_evidence")
        or packet.get("evidence")
    )


def has_candidate(packet: dict[str, Any]) -> bool:
    return bool(
        packet.get("candidate_ids")
        or packet.get("candidates")
        or packet.get("survivors")
    )


def _validated_ids(items: Any, required_status: str) -> list[str]:
    if not isinstance(items, list):
        return []
    out = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if str(item.get("status", "")).upper() != required_status:
            continue
        cid = item.get("candidate_id")
        if cid:
            out.append(str(cid))
    return sorted(set(out))


PROOF_GATES = {
    "source_provenance",
    "point_in_time",
    "out_of_sample",
    "signal_edge",
    "market_edge",
    "execution_reality",
    "prebuild_killer",
    "chief_falsifier",
    "independent_reproducer",
}


def proof_gate(
    result: dict[str, Any],
    upstream_ids: set[str],
) -> tuple[bool, list[str]]:
    cid = str(result.get("candidate_id", ""))
    if not cid or cid not in upstream_ids:
        return False, ["candidate_not_upstream_validated"]
    if str(result.get("status", "")).upper() != "PASS":
        return False, ["independent_reproduction_not_pass"]

    gates = result.get("gates")
    if not isinstance(gates, dict):
        return False, ["missing_structured_gates"]

    failed = sorted(
        gate
        for gate in PROOF_GATES
        if str(gates.get(gate, "")).upper() != "PASS"
    )

    economics = result.get("economics")
    if not isinstance(economics, dict):
        failed.append("missing_economics")
    else:
        for key in (
            "fees",
            "spread",
            "slippage",
            "fills",
            "settlement",
            "capacity",
        ):
            if key not in economics:
                failed.append("economics_" + key)
        if economics.get("net_edge") is None:
            failed.append("economics_net_edge")

    return not failed, failed


def propagate_validation(run_dir: Path) -> dict[str, Any]:
    killer_path = run_dir / "prebuild_killer.json"
    falsifier_path = run_dir / "chief_falsifier.json"
    reproducer_path = run_dir / "independent_reproducer.json"

    killer = load_json(killer_path) if killer_path.exists() else {}
    falsifier = load_json(falsifier_path) if falsifier_path.exists() else {}
    reproducer = load_json(reproducer_path) if reproducer_path.exists() else {}

    killer_pass = _validated_ids(
        killer.get("validation_results"),
        "PASS",
    )
    falsifier["survivors"] = killer_pass
    if (
        killer_pass
        and falsifier.get("status")
        in {"PENDING", "WAITING_FOR_DATA", "READY"}
    ):
        falsifier["status"] = "PENDING"

    falsifier_pass = _validated_ids(
        falsifier.get("validation_results"),
        "PASS",
    )
    reproducer["reproduction_candidates"] = [
        cid for cid in falsifier_pass if cid in set(killer_pass)
    ]
    if (
        reproducer["reproduction_candidates"]
        and reproducer.get("status")
        in {"PENDING", "WAITING_FOR_DATA", "READY"}
    ):
        reproducer["status"] = "PENDING"

    if falsifier_path.exists():
        save_json(falsifier_path, falsifier)

    proof_candidates = []
    proof_rejections = {}
    upstream = set(reproducer.get("reproduction_candidates", []))
    results = reproducer.get("validation_results", [])
    if not isinstance(results, list):
        results = []

    for result in results:
        if not isinstance(result, dict):
            continue
        ok, reasons = proof_gate(result, upstream)
        cid = str(result.get("candidate_id", ""))
        if ok:
            proof_candidates.append(cid)
        elif cid:
            proof_rejections[cid] = reasons

    if reproducer_path.exists():
        save_json(reproducer_path, reproducer)

    return {
        "killer_pass": killer_pass,
        "falsifier_pass": falsifier_pass,
        "reproduction_candidates": reproducer.get(
            "reproduction_candidates", []
        ),
        "proof_candidates": sorted(set(proof_candidates)),
        "proof_rejections": proof_rejections,
        "economic_conclusion": (
            "PROVEN_EDGE_CANDIDATE"
            if proof_candidates
            else "NO_PROVEN_EDGE"
        ),
    }


def decide(packet: dict[str, Any]) -> Decision:
    role = str(packet.get("agent_id", ""))
    current = str(packet.get("status", "PENDING"))

    # A worker-produced NO_EVIDENCE is terminal for this run. A pre-worker
    # NO_EVIDENCE remains re-evaluable so hydration can make new evidence or
    # a deterministic candidate assignment READY in the normal preparation path.
    if current == "NO_EVIDENCE" and isinstance(
        packet.get("ai_result"), dict
    ):
        return Decision(
            current,
            str(packet.get("priority", "P3")),
            "ai_result_preserved",
        )

    if current in {
        "RUNNING",
        "WAITING_FOR_DATA",
        "WAITING_FOR_RESULT",
        "RESULT_READY",
        "COMPLETED",
        "FAILED",
        "FALSIFIED",
        "PARKED",
    }:
        return Decision(
            current,
            str(packet.get("priority", "P3")),
            "existing_state_preserved",
        )

    if role in PRIMARY_ROLES:
        if has_candidate(packet):
            return Decision(
                "READY",
                "P3",
                (
                    "candidate_and_routed_evidence_available"
                    if has_evidence(packet)
                    else "candidate_assignment_available"
                ),
            )
        if has_evidence(packet):
            return Decision(
                "READY",
                "P3",
                "routed_evidence_available",
            )
        return Decision(
            "NO_EVIDENCE",
            "P3",
            "no_routed_evidence",
        )

    if role == "prebuild_killer":
        if has_candidate(packet):
            return Decision(
                "READY",
                "P2",
                "candidate_available_for_prebuild_kill",
            )
        return Decision(
            "WAITING_FOR_DATA",
            "P2",
            "no_candidate_available",
        )

    if role == "chief_falsifier":
        if packet.get("survivors"):
            return Decision(
                "READY",
                "P2",
                "survivor_available_for_falsification",
            )
        return Decision(
            "WAITING_FOR_DATA",
            "P2",
            "no_survivor_available",
        )

    if role == "independent_reproducer":
        if (
            packet.get("reproduction_candidates")
            or packet.get("survivors")
        ):
            return Decision(
                "READY",
                "P2",
                "serious_survivor_available_for_reproduction",
            )
        return Decision(
            "WAITING_FOR_DATA",
            "P2",
            "no_serious_survivor_available",
        )

    if role == "research_director":
        return Decision(
            "READY",
            "P1",
            "director_closes_active_cycle",
        )

    return Decision(
        "PARKED",
        "P3",
        "unknown_agent_role",
    )


def enrich_packet(path: Path) -> dict[str, Any]:
    packet = load_json(path)
    packet["live_trading"] = False
    packet["paid_actions"] = False
    packet["wallet_actions"] = False
    packet["openai_api"] = False

    decision = decide(packet)
    packet["status"] = decision.state
    packet["priority"] = decision.priority
    packet["orchestrator_reason"] = decision.reason
    packet["orchestrator_updated_at_unix"] = int(time.time())
    packet.setdefault("next_decisive_question", None)
    packet.setdefault("local_task_required", False)
    packet.setdefault("local_task_id", None)

    save_json(path, packet)
    return packet


def priority_key(packet: dict[str, Any]) -> tuple[int, int, str]:
    priority = str(packet.get("priority", "P3"))
    created = int(
        packet.get(
            "created_at_unix",
            packet.get(
                "orchestrator_updated_at_unix",
                int(time.time()),
            ),
        )
    )
    return (
        PRIORITIES.get(priority, 99),
        created,
        str(packet.get("agent_id", "")),
    )


def orchestrate(
    run_dir: Path,
    candidate_queue: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not run_dir.is_dir():
        raise FileNotFoundError(run_dir)

    candidate_assignments = hydrate_candidate_routes(
        run_dir,
        candidate_queue,
    )
    validation = propagate_validation(run_dir)
    packets = []

    for path in sorted(run_dir.glob("*.json")):
        if path.name.startswith("_"):
            continue
        packets.append(enrich_packet(path))

    ordered = sorted(packets, key=priority_key)
    queue = [
        {
            "agent_id": packet.get("agent_id"),
            "status": packet.get("status"),
            "priority": packet.get("priority"),
            "reason": packet.get("orchestrator_reason"),
            "candidate_ids": packet.get("candidate_ids", []),
            "candidate_routing": packet.get("candidate_routing", []),
            "local_task_required": packet.get(
                "local_task_required", False
            ),
        }
        for packet in ordered
    ]

    summary = {
        "run_id": run_dir.name,
        "guardrails": {
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
            "openai_api": False,
        },
        "candidate_routing": candidate_assignments,
        "queue": queue,
        "validation_pipeline": validation,
    }

    save_json(run_dir / "_orchestration.json", summary)
    return summary


def latest_run_dir() -> Path:
    if not PACKETS.exists():
        raise FileNotFoundError(PACKETS)

    runs = sorted(path for path in PACKETS.iterdir() if path.is_dir())
    if not runs:
        raise RuntimeError("no agent packet runs found")
    return runs[-1]


if __name__ == "__main__":
    run_dir = latest_run_dir()
    result = orchestrate(run_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
