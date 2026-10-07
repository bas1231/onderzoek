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
