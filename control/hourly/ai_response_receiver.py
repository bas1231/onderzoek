from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import importlib.util
import json
import re
import sys


ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "knowledge/runs"
PACKETS = RUNS / "agent_packets"
RUN_ID_RE = re.compile(r"^hourly-[A-Za-z0-9T:+-]{8,150}$")

# The chat worker may schedule/triage existing candidates, but it may not
# independently kill or promote them. Those transitions belong to the
# killer/falsifier/reproducer/director proof path.
AI_CANDIDATE_STATES = {
    "NEEDS_DIRECTOR",
    "EXPERIMENT_REQUIRED",
    "RUNNING",
    "WAITING_FOR_DATA",
    "WAITING_FOR_RESULT",
    "RESULT_READY",
    "NEEDS_REVISION",
    "PARKED",
}


class ResponseReceiverError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ResponseReceiverError(message)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {name} from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        sys.modules.pop(spec.name, None)
        raise
    return mod


def safe_run_id(value: Any) -> str:
    run_id = str(value or "")
    require(bool(RUN_ID_RE.fullmatch(run_id)), "invalid run_id")
    require("/" not in run_id and "\\" not in run_id and ".." not in run_id, "unsafe run_id")
    return run_id


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def response_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def bundle_path(run_id: str) -> Path:
    return RUNS / f"{safe_run_id(run_id)}-ai-work-bundle.json"


def response_path(run_id: str) -> Path:
    return RUNS / f"{safe_run_id(run_id)}-ai-response.json"


def pending_path(run_id: str) -> Path:
    return RUNS / f"{safe_run_id(run_id)}-ai-response.pending.json"


def receipt_path(run_id: str) -> Path:
    return RUNS / f"{safe_run_id(run_id)}-ai-response-receipt.json"


def load_bundle(run_id: str) -> dict[str, Any]:
    path = bundle_path(run_id)
    require(path.exists(), "AI work bundle missing")
    data = load_json(path)
    require(isinstance(data, dict), "AI work bundle must be object")
    require(data.get("schema") == "PVA_AI_WORK_BUNDLE_V1", "unexpected bundle schema")
    require(data.get("run_id") == run_id, "bundle run_id mismatch")
    token = data.get("response_token")
    require(isinstance(token, str) and len(token) == 64, "bundle response_token missing")
    return data


def expected_ready_roles(run_id: str) -> set[str]:
    data = load_bundle(run_id)
    roles = data.get("ready_roles")
    require(isinstance(roles, list), "bundle ready_roles missing")
    out: set[str] = set()
    for item in roles:
        require(isinstance(item, dict), "invalid ready role")
        aid = item.get("agent_id")
        require(isinstance(aid, str) and bool(aid), "ready role agent_id missing")
        require(aid not in out, f"duplicate ready role: {aid}")
        out.add(aid)
    return out


def bundled_candidate_ids(run_id: str) -> set[str]:
    data = load_bundle(run_id)
    queue = data.get("candidate_queue") or {}
    require(isinstance(queue, dict), "bundle candidate_queue invalid")
    out: set[str] = set()
    for section in (
        "director_attention",
        "waiting_without_blocking",
        "full_queue",
    ):
        items = queue.get(section, [])
        require(isinstance(items, list), f"bundle candidate_queue {section} invalid")
        for item in items:
            if not isinstance(item, dict):
                continue
            cid = item.get("candidate_id")
            if isinstance(cid, str) and cid:
                out.add(cid)
    return out


def validate_complete_role_coverage(response: dict[str, Any], run_id: str) -> None:
    expected = expected_ready_roles(run_id)
    role_results = response.get("role_results")
    require(isinstance(role_results, list), "role_results required")
    actual = {
        str(item.get("agent_id"))
        for item in role_results
        if isinstance(item, dict) and item.get("agent_id")
    }
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    require(not missing, "AI response missing ready roles: " + ",".join(missing))
    require(not extra, "AI response contains non-ready roles: " + ",".join(extra))


def validate_response_token(response: dict[str, Any], run_id: str) -> None:
    bundle = load_bundle(run_id)
    require(
        response.get("response_token") == bundle.get("response_token"),
        "AI response_token mismatch",
    )


def validate_candidate_authority(response: dict[str, Any], run_id: str) -> None:
    allowed_ids = bundled_candidate_ids(run_id)
    decisions = response.get("candidate_decisions", [])
    require(isinstance(decisions, list), "candidate_decisions required")
    for decision in decisions:
        require(isinstance(decision, dict), "candidate decision must be object")
        cid = decision.get("candidate_id")
        require(cid in allowed_ids, f"candidate not present in AI work bundle: {cid}")
        status = decision.get("queue_status")
        require(
            status in AI_CANDIDATE_STATES,
            f"AI worker lacks candidate transition authority: {status}",
        )


def _same_response(path: Path, response: dict[str, Any]) -> bool:
    try:
        return response_sha256(load_json(path)) == response_sha256(response)
    except Exception:
        return False


def _orchestrate(run_id: str):
    orchestrator = load_module(
        "prediction_ai_response_receiver_orchestrator",
        ROOT / "control/hourly/agent_orchestrator.py",
    )
    packet_dir = PACKETS / run_id
    require(packet_dir.is_dir(), "packet directory missing")
    return packet_dir, orchestrator.orchestrate(packet_dir)


def _result(
    run_id: str,
    response: dict[str, Any],
    orchestration: dict[str, Any],
    *,
    already_applied: bool,
) -> dict[str, Any]:
    final = response_path(run_id)
    receipt = receipt_path(run_id)
    packet_dir = PACKETS / run_id
    statuses = {
        item.get("agent_id"): item.get("status")
        for item in orchestration.get("queue", [])
        if item.get("agent_id")
    }
    return {
        "ok": True,
        "run_id": run_id,
        "already_applied": already_applied,
        "response_sha256": response_sha256(response),
        "response_ref": str(final.relative_to(ROOT)),
        "receipt_ref": str(receipt.relative_to(ROOT)) if receipt.exists() else None,
        "orchestration_ref": str((packet_dir / "_orchestration.json").relative_to(ROOT)),
        "role_statuses": statuses,
        "validation_pipeline": orchestration.get("validation_pipeline", {}),
        "economic_conclusion": "NO_PROVEN_EDGE",
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
    }


def receive(payload: dict[str, Any]) -> dict[str, Any]:
    require(isinstance(payload, dict), "payload must be object")
    run_id = safe_run_id(payload.get("run_id"))
    response = payload.get("response")
    require(isinstance(response, dict), "response must be object")
    require(response.get("run_id") == run_id, "response run_id mismatch")
    validate_response_token(response, run_id)

    final = response_path(run_id)
    pending = pending_path(run_id)
    receipt = receipt_path(run_id)

    # Identical retries are recovery opportunities: re-run the derivable
    # orchestration step instead of merely returning success. This repairs a
    # crash after durable response application but before orchestration.
    if final.exists():
        require(_same_response(final, response), "conflicting AI response already stored")
        _, orchestration = _orchestrate(run_id)
        return _result(
            run_id,
            response,
            orchestration,
            already_applied=True,
        )

    ai_response = load_module(
        "prediction_ai_response_receiver_apply",
        ROOT / "control/hourly/ai_response.py",
    )

    # Validate the entire response and mutation plan before any write.
    ai_response.validate_response(response, run_id)
    validate_complete_role_coverage(response, run_id)
    validate_candidate_authority(response, run_id)
    ai_response.apply_response(response, run_id, write=False)

    if pending.exists():
        require(_same_response(pending, response), "conflicting pending AI response")
    else:
        save_json(pending, response)

    if not receipt.exists():
        ai_response.apply_response(response, run_id, write=True)

    # Once packet/candidate changes and their receipt exist, the raw response
    # is durable. Finalize it before the derivable orchestration step so an
    # identical retry can repair an interrupted orchestration.
    pending.replace(final)

    _, orchestration = _orchestrate(run_id)

    return _result(
        run_id,
        response,
        orchestration,
        already_applied=False,
    )
