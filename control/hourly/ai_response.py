from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json


ROOT = Path.cwd()
RUNS = ROOT / "knowledge/runs"
PACKETS = RUNS / "agent_packets"
CANDIDATES = ROOT / "knowledge/candidates"

ROLE_STATES = {
    "COMPLETED",
    "NO_EVIDENCE",
    "FALSIFIED",
    "WAITING_FOR_DATA",
    "WAITING_FOR_RESULT",
    "RESULT_READY",
    "PARKED",
}

QUEUE_STATES = {
    "NEEDS_DIRECTOR",
    "EXPERIMENT_REQUIRED",
    "RUNNING",
    "WAITING_FOR_DATA",
    "WAITING_FOR_RESULT",
    "RESULT_READY",
    "NEEDS_REVISION",
    "PARKED",
    "CLOSED_NEGATIVE",
    "PROMOTION_CANDIDATE",
}

ALLOWED_ROLE_IDS = {
    "recon_scout",
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
}


class ValidationError(ValueError):
    pass


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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def validate_role_result(item: Any) -> None:
    require(isinstance(item, dict), "role result must be object")
    aid = item.get("agent_id")
    require(aid in ALLOWED_ROLE_IDS, f"invalid agent_id: {aid}")
    require(
        item.get("status") in ROLE_STATES,
        f"invalid role status: {item.get('status')}",
    )

    finding = item.get("finding")
    require(
        finding is None or isinstance(finding, str),
        "finding must be string|null",
    )

    refs = item.get("evidence_refs", [])
    require(isinstance(refs, list), "evidence_refs must be list")
    require(
        all(isinstance(value, str) for value in refs),
        "evidence_refs must contain strings",
    )

    candidate_ids = item.get("candidate_ids", [])
    require(isinstance(candidate_ids, list), "candidate_ids must be list")
    require(
        all(isinstance(value, str) for value in candidate_ids),
        "candidate_ids must contain strings",
    )

    local_required = item.get("local_task_required", False)
    require(isinstance(local_required, bool), "local_task_required must be bool")
    spec = item.get("local_task_spec")

    if local_required:
        require(isinstance(spec, dict), "local task requires local_task_spec object")
        forbidden = {"command", "shell", "argv", "exec", "executable"}
        overlap = forbidden.intersection(spec.keys())
        require(
            not overlap,
            "local_task_spec contains executable fields: "
            + ",".join(sorted(overlap)),
        )


def validate_candidate_decision(item: Any) -> None:
    require(isinstance(item, dict), "candidate decision must be object")
    cid = item.get("candidate_id")
    require(isinstance(cid, str) and bool(cid), "candidate_id required")
    status = item.get("queue_status")
    require(status in QUEUE_STATES, f"invalid queue_status: {status}")
    reason = item.get("reason")
    require(
        isinstance(reason, str) and bool(reason.strip()),
        "candidate reason required",
    )


def validate_response(
    response: Any,
    expected_run_id: str,
) -> dict[str, Any]:
    require(isinstance(response, dict), "response must be object")
    require(response.get("run_id") == expected_run_id, "run_id mismatch")
    require(
        response.get("economic_conclusion") == "NO_PROVEN_EDGE",
        "economic_conclusion must remain NO_PROVEN_EDGE",
    )

    role_results = response.get("role_results")
    require(isinstance(role_results, list), "role_results required")
    candidate_decisions = response.get("candidate_decisions")
    require(isinstance(candidate_decisions, list), "candidate_decisions required")
    local_tasks = response.get("local_tasks", [])
    require(isinstance(local_tasks, list), "local_tasks must be list")

    seen_roles = set()
    for item in role_results:
        validate_role_result(item)
        aid = item["agent_id"]
        require(aid not in seen_roles, f"duplicate role: {aid}")
        seen_roles.add(aid)

    seen_candidates = set()
    for item in candidate_decisions:
        validate_candidate_decision(item)
        cid = item["candidate_id"]
        require(cid not in seen_candidates, f"duplicate candidate: {cid}")
        seen_candidates.add(cid)

    forbidden = {"command", "shell", "argv", "exec", "executable"}
    for task in local_tasks:
        require(isinstance(task, dict), "local task must be object")
        overlap = forbidden.intersection(task.keys())
        require(
            not overlap,
            "local_tasks contains executable fields: "
            + ",".join(sorted(overlap)),
        )

    for key in {
        "live_trading",
        "paid_actions",
        "wallet_actions",
        "openai_api",
    }:
        require(
            response.get(key) not in {True, "true", "TRUE", 1},
            f"forbidden action requested: {key}",
        )

    return response


def candidate_path(candidate_id: str) -> Path:
    require(
        "/" not in candidate_id
        and "\\" not in candidate_id
        and ".." not in candidate_id,
        "unsafe candidate_id",
    )
    return CANDIDATES / f"{candidate_id}.json"


def apply_response(
    response: dict[str, Any],
    expected_run_id: str,
    *,
    write: bool = False,
) -> dict[str, Any]:
    validated = validate_response(response, expected_run_id)
    packet_dir = PACKETS / expected_run_id
    require(packet_dir.is_dir(), "packet directory missing")

    packet_updates = []
    candidate_updates = []

    for result in validated["role_results"]:
        aid = result["agent_id"]
        path = packet_dir / f"{aid}.json"
        require(path.exists(), f"packet missing: {aid}")
        packet = load_json(path)
        require(
            packet.get("run_id") == expected_run_id,
            f"packet run mismatch: {aid}",
        )

        updated = dict(packet)
        updated["status"] = result["status"]
        updated["ai_result"] = {
            "finding": result.get("finding"),
            "evidence_refs": result.get("evidence_refs", []),
            "candidate_ids": result.get("candidate_ids", []),
            "next_decisive_question": result.get("next_decisive_question"),
            "local_task_required": result.get("local_task_required", False),
            "local_task_spec": result.get("local_task_spec"),
            "applied_at": now_iso(),
        }
        updated["live_trading"] = False
        updated["paid_actions"] = False
        updated["wallet_actions"] = False
        packet_updates.append((path, updated))

    for decision in validated["candidate_decisions"]:
        cid = decision["candidate_id"]
        path = candidate_path(cid)
        require(path.exists(), f"candidate missing: {cid}")
        candidate = load_json(path)
        updated = dict(candidate)
        updated["queue_status"] = decision["queue_status"]
        updated["queue_reason"] = decision["reason"]
        if "next_decisive_test" in decision:
            updated["next_decisive_test"] = decision.get("next_decisive_test")
        updated["updated_at"] = now_iso()
        updated["live_trading"] = False
        updated["paid_actions"] = False
        updated["wallet_actions"] = False
        candidate_updates.append((path, updated))

    receipt = {
        "schema": "PVA_AI_RESPONSE_RECEIPT_V1",
        "run_id": expected_run_id,
        "validated_at": now_iso(),
        "write": write,
        "packet_updates": [str(path.relative_to(ROOT)) for path, _ in packet_updates],
        "candidate_updates": [
            str(path.relative_to(ROOT)) for path, _ in candidate_updates
        ],
        "local_task_requests": validated.get("local_tasks", []),
        "guardrails": {
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
            "openai_api": False,
        },
    }

    if write:
        for path, obj in packet_updates:
            save_json(path, obj)
        for path, obj in candidate_updates:
            save_json(path, obj)
        receipt_path = RUNS / f"{expected_run_id}-ai-response-receipt.json"
        save_json(receipt_path, receipt)
        receipt["receipt_path"] = str(receipt_path.relative_to(ROOT))

    return receipt


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--response", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    response = load_json(Path(args.response))
    receipt = apply_response(response, args.run_id, write=args.write)
    print(json.dumps(receipt, indent=2, sort_keys=True))
