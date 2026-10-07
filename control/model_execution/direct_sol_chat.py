from __future__ import annotations

import hashlib
from typing import Any

REQUEST_SCHEMA = "PREDICTION_DIRECT_SOL_REQUEST_V1"
RESULT_SCHEMA = "PREDICTION_DIRECT_SOL_RESULT_V1"
PROVENANCE_KIND = "CHATGPT_REGULAR_CHAT_DIRECT_SOL"
EXECUTION_LAYER = "DIRECT_SOL_CHAT"
TARGET_MODEL = "gpt-5.6-sol"
TARGET_DISPLAY = "GPT-5.6 Sol"
TARGET_EXPERIENCE = "CHAT"
SOL_PHASES = {"SOL_PROPOSAL", "SOL_BUILD"}
SAFETY_KEYS = ("live_trading", "paid_actions", "wallet_actions")


class DirectSolError(ValueError):
    pass


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def require_route(value: Any, field: str) -> str:
    route = str(value or "")
    if not route.startswith("SESSION-ROUTE-"):
        raise DirectSolError(field + "_REQUIRED")
    return route


def require_safety_false(value: dict[str, Any]) -> None:
    for key in SAFETY_KEYS:
        if value.get(key) is not False:
            raise DirectSolError("DIRECT_SOL_SAFETY:" + key)


def validate_request(request: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(request, dict) or request.get("schema") != REQUEST_SCHEMA:
        raise DirectSolError("DIRECT_SOL_REQUEST_SCHEMA")
    if str(request.get("phase") or "") not in SOL_PHASES:
        raise DirectSolError("DIRECT_SOL_PHASE")
    if request.get("target_model") != TARGET_MODEL:
        raise DirectSolError("DIRECT_SOL_EXACT_MODEL_REQUIRED")
    if request.get("target_experience") != TARGET_EXPERIENCE:
        raise DirectSolError("DIRECT_SOL_REGULAR_CHAT_REQUIRED")
    if request.get("execution_layer") != EXECUTION_LAYER:
        raise DirectSolError("DIRECT_SOL_EXECUTION_LAYER")
    require_route(request.get("delivery_route_task_id"), "DIRECT_SOL_DELIVERY_ROUTE")
    prompt = request.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise DirectSolError("DIRECT_SOL_PROMPT_REQUIRED")
    if request.get("input_sha256") != sha256_text(prompt):
        raise DirectSolError("DIRECT_SOL_INPUT_HASH")
    for key in ("task_id", "campaign_id", "candidate_id", "binding_sha256"):
        if not isinstance(request.get(key), str) or not request[key]:
            raise DirectSolError("DIRECT_SOL_REQUEST_FIELD:" + key)
    require_safety_false(request)
    return request


def build_request(
    *,
    task_id: str,
    phase: str,
    campaign_id: str,
    candidate_id: str,
    binding_sha256: str,
    prompt: str,
    delivery_route_task_id: str,
    created_at_utc: str,
) -> dict[str, Any]:
    request = {
        "schema": REQUEST_SCHEMA,
        "task_id": task_id,
        "phase": phase,
        "campaign_id": campaign_id,
        "candidate_id": candidate_id,
        "binding_sha256": binding_sha256,
        "prompt": prompt,
        "input_sha256": sha256_text(prompt),
        "target_model": TARGET_MODEL,
        "target_model_display": TARGET_DISPLAY,
        "target_experience": TARGET_EXPERIENCE,
        "execution_layer": EXECUTION_LAYER,
        "delivery_route_task_id": delivery_route_task_id,
        "created_at_utc": created_at_utc,
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
    }
    return validate_request(request)


def validate_result(request: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    validate_request(request)
    if not isinstance(result, dict) or result.get("schema") != RESULT_SCHEMA:
        raise DirectSolError("DIRECT_SOL_RESULT_SCHEMA")
    require_safety_false(result)
    exact = {
        "task_id": request["task_id"],
        "phase": request["phase"],
        "campaign_id": request["campaign_id"],
        "candidate_id": request["candidate_id"],
        "binding_sha256": request["binding_sha256"],
        "input_sha256": request["input_sha256"],
        "model": TARGET_MODEL,
        "model_display": TARGET_DISPLAY,
        "experience": TARGET_EXPERIENCE,
        "execution_layer": EXECUTION_LAYER,
        "provenance_kind": PROVENANCE_KIND,
    }
    for key, expected in exact.items():
        if result.get(key) != expected:
            raise DirectSolError("DIRECT_SOL_RESULT_MISMATCH:" + key)
    require_route(result.get("worker_route_task_id"), "DIRECT_SOL_WORKER_ROUTE")
    if result.get("work_mode") is not False or result.get("codex") is not False:
        raise DirectSolError("DIRECT_SOL_NOT_REGULAR_CHAT")
    if result.get("tools_used") not in ([], None):
        raise DirectSolError("DIRECT_SOL_MODEL_TOOLS_FORBIDDEN")
    final = result.get("final")
    if not isinstance(final, str) or not final.strip():
        raise DirectSolError("DIRECT_SOL_FINAL_REQUIRED")
    if result.get("completion_sha256") != sha256_text(final):
        raise DirectSolError("DIRECT_SOL_COMPLETION_HASH")
    for key in ("started_at_utc", "finished_at_utc"):
        if not isinstance(result.get(key), str) or not result[key]:
            raise DirectSolError("DIRECT_SOL_RESULT_FIELD:" + key)
    return result


def build_result(
    request: dict[str, Any],
    *,
    worker_route_task_id: str,
    final: str,
    started_at_utc: str,
    finished_at_utc: str,
) -> dict[str, Any]:
    validate_request(request)
    result = {
        "schema": RESULT_SCHEMA,
        "task_id": request["task_id"],
        "phase": request["phase"],
        "campaign_id": request["campaign_id"],
        "candidate_id": request["candidate_id"],
        "binding_sha256": request["binding_sha256"],
        "input_sha256": request["input_sha256"],
        "model": TARGET_MODEL,
        "model_display": TARGET_DISPLAY,
        "experience": TARGET_EXPERIENCE,
        "execution_layer": EXECUTION_LAYER,
        "provenance_kind": PROVENANCE_KIND,
        "worker_route_task_id": worker_route_task_id,
        "work_mode": False,
        "codex": False,
        "tools_used": [],
        "final": final,
        "completion_sha256": sha256_text(final),
        "started_at_utc": started_at_utc,
        "finished_at_utc": finished_at_utc,
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
    }
    return validate_result(request, result)
