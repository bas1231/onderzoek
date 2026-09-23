from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib
import json


ROOT = Path.cwd()
RUNS = ROOT / "knowledge/runs"
PACKETS = RUNS / "agent_packets"

READY_STATES = {"READY", "RESULT_READY"}
ROLE_ORDER = [
    "discovery",
    "market_research",
    "mechanics",
    "algebra",
    "red_team_pentest",
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
        "coverage_gaps_by_capability": packet.get("coverage_gaps_by_capability", {}),
        "capability_work": packet.get("capability_work", {}),
        "discovery_lanes": packet.get("discovery_lanes", {}),
        "candidate_ids": packet.get("candidate_ids", []),
        "candidate_routing": packet.get("candidate_routing", []),
        "red_team_modes": packet.get("red_team_modes", {}),
        "reproduction_candidates": packet.get("reproduction_candidates", []),
        "blind_reproduction_interface": packet.get("blind_reproduction_interface", []),
        "blind": bool(packet.get("blind", False)),
        "transient": bool(packet.get("transient", False)),
        "recon_watch_triage": packet.get("recon_watch_triage", []),
        "recon_hunts": packet.get("recon_hunts", []),
        "task_shape": packet.get("task_shape"),
        "scheduler_priority": packet.get("scheduler_priority"),
        "dynamic_worker_scheduled": packet.get("dynamic_worker_scheduled"),
        "next_decisive_question": packet.get("next_decisive_question"),
        "local_task_required": packet.get("local_task_required", False),
        "local_task_id": packet.get("local_task_id"),
    }


def response_token(
    run_id: str,
    ready_roles: list[dict[str, Any]],
    candidate_queue: dict[str, Any],
) -> str:
    material = {
        "run_id": run_id,
        "ready_roles": ready_roles,
        "candidate_queue": candidate_queue,
    }
    encoded = json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build(run_id: str) -> tuple[dict[str, Any], Path]:
    packet_dir = PACKETS / run_id
    if not packet_dir.is_dir():
        raise FileNotFoundError(packet_dir)

    handoff_path = RUNS / f"{run_id}-director-handoff.json"
    if not handoff_path.exists():
        raise FileNotFoundError(handoff_path)
    director_handoff = load_json(handoff_path)

    # AI_BUNDLE_CREATE_ONCE_E002
    # One hourly run_id represents one immutable AI work snapshot. Re-running
    # the same hour must reuse that snapshot instead of silently changing the
    # response token while a create-only request may already be in flight.
    out = RUNS / f"{run_id}-ai-work-bundle.json"
    if out.exists():
        existing = load_json(out)
        if not isinstance(existing, dict):
            raise ValueError("existing AI work bundle must be object")
        if existing.get("schema") != "PVA_AI_WORK_BUNDLE_V1":
            raise ValueError("existing AI work bundle schema mismatch")
        if existing.get("run_id") != run_id:
            raise ValueError("existing AI work bundle run_id mismatch")

        token = existing.get("response_token")
        if not isinstance(token, str) or len(token) != 64:
            raise ValueError("existing AI work bundle token invalid")

        ready_roles = existing.get("ready_roles")
        if not isinstance(ready_roles, list):
            raise ValueError("existing AI work bundle ready_roles invalid")

        guardrails = existing.get("guardrails") or {}
        for key in (
            "live_trading",
            "paid_actions",
            "wallet_actions",
            "openai_api",
        ):
            if guardrails.get(key) is not False:
                raise ValueError(
                    f"existing AI work bundle unsafe guardrail: {key}"
                )

        expected = existing.get("expected_response_schema") or {}
        if expected.get("response_token") != token:
            raise ValueError(
                "existing AI work bundle expected response token mismatch"
            )

        return existing, out

    packets: dict[str, dict[str, Any]] = {}
    for path in packet_dir.glob("*.json"):
        if path.name.startswith("_"):
            continue
        packet = load_json(path)
        aid = packet.get("agent_id")
        if aid:
            packets[str(aid)] = packet

    ready_roles = []
    for aid in ROLE_ORDER:
        packet = packets.get(aid)
        if packet and packet.get("status") in READY_STATES:
            ready_roles.append(compact_packet(packet))

    candidate_queue = {
        "director_attention": director_handoff.get("director_attention", []),
        "waiting_without_blocking": director_handoff.get("waiting_without_blocking", []),
        "full_queue": director_handoff.get("full_queue", []),
    }
    token = response_token(run_id, ready_roles, candidate_queue)

    task_schedule_path = packet_dir / "_task_schedule.json"
    task_schedule = load_json(task_schedule_path) if task_schedule_path.exists() else {}

    bundle = {
        "schema": "PVA_AI_WORK_BUNDLE_V1",
        "architecture": "E007_SIX_DOMAIN",
        "run_id": run_id,
        "response_token": token,
        "created_at": now_iso(),
        "delivery_policy": {
            "single_chatgpt_turn": True,
            "one_bundle_per_cycle": True,
            "specialist_browser_requests": False,
            "local_compute_only_when_decisive": True,
            "waiting_does_not_block_other_work": True,
            "max_permanent_specialist_domains": 5,
            "transient_reproducer_isolated": True,
        },
        "research_policy": {
            "default_economic_conclusion": "NO_PROVEN_EDGE",
            "no_starvation": True,
            "promotion_requires_evidence": True,
            "watch_triage_is_not_promotion": True,
            "watch_triage_promotion_authority": False,
            "ai_candidate_kill_authority": False,
            "ai_candidate_promotion_authority": False,
            "kill_is_not_delete": True,
            "negative_evidence_must_be_preserved": True,
            "protected_discovery_lanes": ["primary_scout", "recon_scout"],
            "red_team_modes": ["QUICK_KILL", "DEEP_FALSIFICATION"],
        },
        "guardrails": {
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
            "openai_api": False,
        },
        "task_schedule": task_schedule,
        "ready_roles": ready_roles,
        "candidate_queue": candidate_queue,
        "director_instruction": (
            "Operate the E007 six-domain Research OS. Evaluate every bundled ready role exactly once. "
            "Legacy specialist names inside capability_work are capabilities, not extra agents. Keep "
            "Discovery primary_scout and recon_scout findings/provenance separate before synthesis. "
            "Market Research must keep weather/TWC, behavioral and informed-flow evidence labelled by "
            "capability. Mechanics must separate settlement/finality from executable microstructure. "
            "Red Team/Pentest must use QUICK_KILL for cheap early falsification and DEEP_FALSIFICATION "
            "only where red_team_modes requests it. The transient Independent Reproducer is blind: do "
            "not infer or reconstruct withheld originating conclusions; reproduce from the supplied "
            "interface and independent evidence. Preserve negative evidence and cite failure-pattern IDs "
            "FP-001..FP-036 when applicable. Every validation_results item must contain status=PASS|FAIL|INCONCLUSIVE|WAITING; mode may be QUICK_KILL, DEEP_FALSIFICATION or REPRODUCTION. Never use result in place of the required status field. Do not invent missing evidence. AI may schedule, wait, revise "
            "or park bundled candidates but may not close-negative or promote them. Return exactly schema "
            "PVA_AI_RESPONSE_V1 and echo response_token. Include capability_results for consolidated "
            "domains and validation_results for Red Team/Reproducer when applicable. NO_PROVEN_EDGE is "
            "valid. Never authorize live trading, paid actions, wallet actions or paid OpenAI API use."
        ),
        "expected_response_schema": {
            "schema": "PVA_AI_RESPONSE_V1",
            "run_id": run_id,
            "response_token": token,
            "role_results": [
                {
                    "agent_id": "discovery|market_research|mechanics|algebra|red_team_pentest|independent_reproducer|research_director",
                    "status": "COMPLETED|NO_EVIDENCE|FALSIFIED|WAITING_FOR_DATA|WAITING_FOR_RESULT|RESULT_READY|PARKED",
                    "finding": "string|null",
                    "evidence_refs": ["string"],
                    "candidate_ids": ["string"],
                    "capability_results": {},
                    # VALIDATION_RESULT_CONTRACT_E003
                    "validation_results": [
                        {
                            "candidate_id": "string|null",
                            "status": "PASS|FAIL|INCONCLUSIVE|WAITING",
                            "mode": "QUICK_KILL|DEEP_FALSIFICATION|REPRODUCTION|null",
                        }
                    ],
                    "failure_pattern_ids": ["FP-xxx"],
                    "next_decisive_question": "string|null",
                    "local_task_required": False,
                    "local_task_spec": None,
                }
            ],
            "candidate_decisions": [
                {
                    "candidate_id": "string",
                    "queue_status": "NEEDS_DIRECTOR|EXPERIMENT_REQUIRED|RUNNING|WAITING_FOR_DATA|WAITING_FOR_RESULT|RESULT_READY|NEEDS_REVISION|PARKED",
                    "reason": "string",
                    "next_decisive_test": "string|null",
                    "resurrection_condition": "string|null",
                }
            ],
            "director_decision": "string",
            "economic_conclusion": "NO_PROVEN_EDGE",
            "local_tasks": [],
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
            "openai_api": False,
        },
    }

    save_json(out, bundle)
    return bundle, out


def latest_run_id() -> str:
    dirs = sorted(
        path for path in PACKETS.iterdir()
        if path.is_dir() and path.name.startswith("hourly-")
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
        "ready_roles": [item["agent_id"] for item in bundle["ready_roles"]],
        "architecture": bundle["architecture"],
        "guardrails": bundle["guardrails"],
    }, indent=2, sort_keys=True))
