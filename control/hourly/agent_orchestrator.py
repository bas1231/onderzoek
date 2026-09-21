from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import time


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

# PVA resource priority:
# P0 system safety
# P1 running/prospective evidence
# P2 decisive falsification/reproduction
# P3 discovery/build
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


def decide(packet: dict[str, Any]) -> Decision:
    role = str(packet.get("agent_id", ""))

    # Never overwrite terminal/in-flight states.
    current = str(packet.get("status", "PENDING"))
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
        if packet.get("reproduction_candidates") or packet.get("survivors"):
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

    # Hard guardrails stay authoritative.
    packet["live_trading"] = False
    packet["paid_actions"] = False
    packet["wallet_actions"] = False

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

    # Older work wins inside the same priority:
    # simple no-starvation mechanism.
    created = int(
        packet.get(
            "created_at_unix",
            packet.get("orchestrator_updated_at_unix", int(time.time())),
        )
    )

    return (
        PRIORITIES.get(priority, 99),
        created,
        str(packet.get("agent_id", "")),
    )


def orchestrate(run_dir: Path) -> dict[str, Any]:
    if not run_dir.is_dir():
        raise FileNotFoundError(run_dir)

    packets = []

    for path in sorted(run_dir.glob("*.json")):
        packets.append(enrich_packet(path))

    ordered = sorted(packets, key=priority_key)

    queue = [
        {
            "agent_id": p.get("agent_id"),
            "status": p.get("status"),
            "priority": p.get("priority"),
            "reason": p.get("orchestrator_reason"),
            "local_task_required": p.get("local_task_required", False),
        }
        for p in ordered
    ]

    summary = {
        "run_id": run_dir.name,
        "guardrails": {
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
        },
        "queue": queue,
    }

    save_json(run_dir / "_orchestration.json", summary)
    return summary


def latest_run_dir() -> Path:
    if not PACKETS.exists():
        raise FileNotFoundError(PACKETS)

    runs = sorted(
        p for p in PACKETS.iterdir()
        if p.is_dir()
    )

    if not runs:
        raise RuntimeError("no agent packet runs found")

    return runs[-1]


if __name__ == "__main__":
    run_dir = latest_run_dir()
    result = orchestrate(run_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
