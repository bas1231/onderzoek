from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json


ROOT = Path.cwd()
RUNS = ROOT / "knowledge/runs"
PACKETS = RUNS / "agent_packets"

READY_STATES = {"READY", "RESULT_READY"}

ROLE_ORDER = [
    "scout",
    "algebra",
    "settlement",
    "microstructure",
    "behavioral",
    "informed_flow",
    "weather_twc",
    "prebuild_killer",
    "chief_falsifier",
    "independent_reproducer",
    "research_director",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, obj: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(obj, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def compact_packet(packet: dict[str, Any]) -> dict[str, Any]:
    return {
        "agent_id": packet.get("agent_id"),
        "status": packet.get("status"),
        "priority": packet.get("priority"),
        "orchestrator_reason": packet.get("orchestrator_reason"),
        "contract": packet.get("contract"),
        "input_refs": packet.get("input_refs", []),
        "routed_evidence": packet.get("routed_evidence", []),
        "coverage_gaps": packet.get("coverage_gaps", []),
        "candidate_ids": packet.get("candidate_ids", []),
        "survivors": packet.get("survivors", []),
        "next_decisive_question": packet.get(
            "next_decisive_question"
        ),
        "local_task_required": packet.get(
            "local_task_required", False
        ),
        "local_task_id": packet.get("local_task_id"),
    }


def build(run_id: str) -> tuple[dict[str, Any], Path]:
    packet_dir = PACKETS / run_id
    if not packet_dir.is_dir():
        raise FileNotFoundError(packet_dir)

    handoff_path = RUNS / f"{run_id}-director-handoff.json"
    if not handoff_path.exists():
        raise FileNotFoundError(handoff_path)

    director_handoff = load_json(handoff_path)

    packets: dict[str, dict[str, Any]] = {}

    for p in packet_dir.glob("*.json"):
        if p.name.startswith("_"):
            continue

        packet = load_json(p)
        aid = packet.get("agent_id")

        if aid:
            packets[aid] = packet

    ready_roles = []

    for aid in ROLE_ORDER:
        packet = packets.get(aid)
        if not packet:
            continue

        if packet.get("status") in READY_STATES:
            ready_roles.append(compact_packet(packet))

    bundle = {
        "schema": "PVA_AI_WORK_BUNDLE_V1",
        "run_id": run_id,
        "created_at": now_iso(),

        # One ChatGPT reasoning turn should consume this entire bundle.
        # Do not create one browser/bridge request per specialist.
        "delivery_policy": {
            "single_chatgpt_turn": True,
            "one_bundle_per_cycle": True,
            "specialist_browser_requests": False,
            "local_compute_only_when_decisive": True,
            "waiting_does_not_block_other_work": True,
        },

        "research_policy": {
            "default_economic_conclusion": "NO_PROVEN_EDGE",
            "priority_order": [
                "P0_SYSTEM_SAFETY",
                "P1_RUNNING_PROSPECTIVE_EVIDENCE",
                "P2_DECISIVE_RESEARCH",
                "P3_DISCOVERY_BUILD",
            ],
            "no_starvation": True,
            "promotion_requires_evidence": True,
        },

        "guardrails": {
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
            "openai_api": False,
        },

        "ready_roles": ready_roles,

        "candidate_queue": {
            "director_attention": director_handoff.get(
                "director_attention", []
            ),
            "waiting_without_blocking": director_handoff.get(
                "waiting_without_blocking", []
            ),
            "full_queue": director_handoff.get(
                "full_queue", []
            ),
        },

        "director_instruction": (
            "Act as the Research Director for this complete bundle. "
            "Evaluate routed evidence role-by-role under each role contract. "
            "Do not invent missing evidence. Preserve negative evidence. "
            "Apply Pre-Build Killer before expensive work and Chief "
            "Falsifier before promotion. Use Independent Reproducer only "
            "for serious survivors. Waiting local computation must not "
            "block unrelated candidates. Request local computation only "
            "when it answers a concrete decisive question. Queue such work "
            "as WAITING_FOR_RESULT and continue other research. "
            "NO_PROVEN_EDGE is a valid conclusion. Never authorize live "
            "trading, paid actions, wallet actions or paid OpenAI API use."
        ),

        "expected_response_schema": {
            "run_id": run_id,
            "role_results": [
                {
                    "agent_id": "string",
                    "status": (
                        "COMPLETED|NO_EVIDENCE|FALSIFIED|"
                        "WAITING_FOR_DATA|WAITING_FOR_RESULT|"
                        "RESULT_READY|PARKED"
                    ),
                    "finding": "string|null",
                    "evidence_refs": ["string"],
                    "candidate_ids": ["string"],
                    "next_decisive_question": "string|null",
                    "local_task_required": False,
                    "local_task_spec": None,
                }
            ],
            "candidate_decisions": [
                {
                    "candidate_id": "string",
                    "queue_status": (
                        "NEEDS_DIRECTOR|EXPERIMENT_REQUIRED|RUNNING|"
                        "WAITING_FOR_DATA|WAITING_FOR_RESULT|"
                        "RESULT_READY|NEEDS_REVISION|PARKED|"
                        "CLOSED_NEGATIVE|PROMOTION_CANDIDATE"
                    ),
                    "reason": "string",
                    "next_decisive_test": "string|null",
                }
            ],
            "director_decision": "string",
            "economic_conclusion": "NO_PROVEN_EDGE",
            "local_tasks": [],
        },
    }

    out = RUNS / f"{run_id}-ai-work-bundle.json"
    save_json(out, bundle)

    return bundle, out


def latest_run_id() -> str:
    dirs = sorted(
        p for p in PACKETS.iterdir()
        if p.is_dir() and p.name.startswith("hourly-")
    )
    if not dirs:
        raise RuntimeError("no packet runs")
    return dirs[-1].name


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id")
    args = parser.parse_args()

    run_id = args.run_id or latest_run_id()
    bundle, path = build(run_id)

    print(json.dumps({
        "ok": True,
        "run_id": run_id,
        "path": str(path.relative_to(ROOT)),
        "ready_roles": [
            x["agent_id"]
            for x in bundle["ready_roles"]
        ],
        "director_attention": len(
            bundle["candidate_queue"]["director_attention"]
        ),
        "waiting_without_blocking": len(
            bundle["candidate_queue"]["waiting_without_blocking"]
        ),
        "single_chatgpt_turn":
            bundle["delivery_policy"]["single_chatgpt_turn"],
        "guardrails": bundle["guardrails"],
    }, indent=2, sort_keys=True))
