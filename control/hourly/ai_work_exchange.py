from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib
import json
import subprocess


ROOT = Path(__file__).resolve().parents[2]
LOCAL_EXCHANGE = ROOT / "knowledge/ai_exchange"
REQUESTS = LOCAL_EXCHANGE / "requests"

REQUEST_SCHEMA = "PVA_AI_EXCHANGE_REQUEST_V1"
RESPONSE_SCHEMA = "PVA_AI_EXCHANGE_RESPONSE_V1"

# Compatibility bridge between the current V13 role universe and Research OS V1.
# The legacy agent_id remains authoritative for PVA_AI_RESPONSE_V1 so the proven
# V13 receiver can stay unchanged.  responsibility/capability describe the work
# semantically and may later replace permanent role personas without changing
# transport.
ROLE_CAPABILITIES: dict[str, tuple[str, str]] = {
    "recon_scout": ("RECON_SCOUT", "DISCOVERY"),
    "scout": ("PRIMARY_SCOUT", "DISCOVERY"),
    "weather_twc": ("SPECIALIST_DISPATCH", "MARKET_RESEARCH"),
    "behavioral": ("SPECIALIST_DISPATCH", "MARKET_RESEARCH"),
    "informed_flow": ("SPECIALIST_DISPATCH", "MARKET_RESEARCH"),
    "settlement": ("SPECIALIST_DISPATCH", "MECHANICS"),
    "microstructure": ("SPECIALIST_DISPATCH", "MECHANICS"),
    "algebra": ("SPECIALIST_DISPATCH", "ALGEBRA"),
    "prebuild_killer": ("RED_TEAM", "QUICK_KILL"),
    "chief_falsifier": ("RED_TEAM", "DEEP_FALSIFICATION"),
    "independent_reproducer": (
        "TEMPORARY_INDEPENDENT_REPRODUCER",
        "INDEPENDENT_REPRODUCTION",
    ),
    "research_director": ("RESEARCH_DIRECTOR", "ADJUDICATION"),
}


class ExchangeContractError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ExchangeContractError(message)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def sha256_obj(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def current_commit() -> str | None:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except Exception:
        return None
    value = proc.stdout.strip()
    if proc.returncode == 0 and len(value) == 40:
        return value
    return None


def work_id(run_id: str, response_token: str, agent_id: str) -> str:
    material = f"{run_id}\n{response_token}\n{agent_id}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def task_shape(agent_id: str) -> str:
    if agent_id in {"settlement", "microstructure", "algebra"}:
        return "SEQUENTIAL"
    if agent_id in {
        "prebuild_killer",
        "chief_falsifier",
        "independent_reproducer",
        "research_director",
    }:
        return "PARTIAL"
    return "PARALLEL"


def validate_bundle(bundle: Any) -> dict[str, Any]:
    require(isinstance(bundle, dict), "bundle must be object")
    require(
        bundle.get("schema") == "PVA_AI_WORK_BUNDLE_V1",
        "unexpected bundle schema",
    )
    run_id = bundle.get("run_id")
    require(
        isinstance(run_id, str) and run_id.startswith("hourly-"),
        "invalid run_id",
    )
    token = bundle.get("response_token")
    require(
        isinstance(token, str)
        and len(token) == 64
        and all(ch in "0123456789abcdef" for ch in token),
        "invalid response_token",
    )
    ready = bundle.get("ready_roles")
    require(isinstance(ready, list), "ready_roles must be list")

    seen: set[str] = set()
    for packet in ready:
        require(isinstance(packet, dict), "ready role must be object")
        agent_id = packet.get("agent_id")
        require(
            isinstance(agent_id, str) and agent_id in ROLE_CAPABILITIES,
            f"unsupported ready role: {agent_id}",
        )
        require(agent_id not in seen, f"duplicate ready role: {agent_id}")
        seen.add(agent_id)

    guardrails = bundle.get("guardrails") or {}
    for key in ("live_trading", "paid_actions", "wallet_actions", "openai_api"):
        require(guardrails.get(key) is False, f"unsafe/missing guardrail: {key}")
    return bundle


def build_request(
    bundle: dict[str, Any],
    *,
    source_commit: str | None = None,
) -> dict[str, Any]:
    data = validate_bundle(bundle)
    run_id = str(data["run_id"])
    token = str(data["response_token"])

    work_items: list[dict[str, Any]] = []
    for packet in data["ready_roles"]:
        agent_id = str(packet["agent_id"])
        responsibility, capability = ROLE_CAPABILITIES[agent_id]
        work_items.append({
            "work_id": work_id(run_id, token, agent_id),
            "agent_id": agent_id,
            "legacy_role": agent_id,
            "responsibility": responsibility,
            "capability_mode": capability,
            "task_shape": task_shape(agent_id),
            "priority": packet.get("priority", "P3"),
            "objective": packet.get("next_decisive_question"),
            "packet": packet,
            "must_return_result": True,
        })

    source = source_commit if source_commit is not None else current_commit()
    request = {
        "schema": REQUEST_SCHEMA,
        "run_id": run_id,
        "response_token": token,
        "created_at": now_iso(),
        "source_commit": source,
        "request_sha256": None,
        "transport": {
            "transport_neutral": True,
            "browser_bridge_required": False,
            "preferred_transport": "git",
            "response_branch": "ai/runtime-exchange",
            "response_path": f"ai_exchange/responses/{run_id}.json",
        },
        "governor": {
            "economic_conclusion": "NO_PROVEN_EDGE",
            "watch_is_not_hunt": True,
            "watch_has_no_promotion_authority": True,
            "ai_candidate_promotion_authority": False,
            "ai_candidate_kill_authority": False,
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
            "openai_api": False,
        },
        "work_items": work_items,
        "candidate_queue": data.get("candidate_queue", {}),
        "director_instruction": data.get("director_instruction"),
        "expected_response_schema": data.get("expected_response_schema"),
    }
    digest_input = dict(request)
    digest_input["request_sha256"] = None
    request["request_sha256"] = sha256_obj(digest_input)
    return request


def validate_request(request: Any) -> dict[str, Any]:
    require(isinstance(request, dict), "request must be object")
    require(request.get("schema") == REQUEST_SCHEMA, "unexpected request schema")
    run_id = request.get("run_id")
    require(isinstance(run_id, str) and run_id.startswith("hourly-"), "invalid run_id")
    token = request.get("response_token")
    require(isinstance(token, str) and len(token) == 64, "invalid response_token")
    work_items = request.get("work_items")
    require(isinstance(work_items, list), "work_items must be list")

    roles: set[str] = set()
    ids: set[str] = set()
    for item in work_items:
        require(isinstance(item, dict), "work item must be object")
        aid = item.get("agent_id")
        require(aid in ROLE_CAPABILITIES, f"unsupported work item role: {aid}")
        require(aid not in roles, f"duplicate work item role: {aid}")
        roles.add(str(aid))
        wid = item.get("work_id")
        require(isinstance(wid, str) and len(wid) == 64, "invalid work_id")
        require(wid not in ids, "duplicate work_id")
        ids.add(wid)
        responsibility, capability = ROLE_CAPABILITIES[str(aid)]
        require(item.get("responsibility") == responsibility, "responsibility mismatch")
        require(item.get("capability_mode") == capability, "capability mismatch")

    governor = request.get("governor") or {}
    require(governor.get("economic_conclusion") == "NO_PROVEN_EDGE", "unsafe economics default")
    for key in ("live_trading", "paid_actions", "wallet_actions", "openai_api"):
        require(governor.get(key) is False, f"unsafe governor flag: {key}")
    require(governor.get("watch_has_no_promotion_authority") is True, "WATCH authority widened")

    supplied = request.get("request_sha256")
    require(isinstance(supplied, str) and len(supplied) == 64, "request_sha256 missing")
    digest_input = dict(request)
    digest_input["request_sha256"] = None
    require(sha256_obj(digest_input) == supplied, "request_sha256 mismatch")
    return request


def write_request(request: dict[str, Any]) -> Path:
    validated = validate_request(request)
    run_id = str(validated["run_id"])
    path = REQUESTS / f"{run_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(validated, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)
    return path


def build_and_write(
    bundle: dict[str, Any],
    *,
    source_commit: str | None = None,
) -> tuple[dict[str, Any], Path]:
    request = build_request(bundle, source_commit=source_commit)
    return request, write_request(request)
