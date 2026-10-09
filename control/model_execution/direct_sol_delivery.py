"""Deliver a published DIRECT_SOL request using the installed continuation API.

This module is application code. It neither selects a model nor creates/imports
model completions. Delivery/ACK and execution are deliberately separate.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import re
import time
from pathlib import Path

from control.model_execution.direct_sol_chat import DirectSolError, validate_request
from control.model_execution.materialize_direct_sol import _immutable_json

TASK_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,119}")
COMMIT_RE = re.compile(r"[0-9a-f]{40}")


def published_request(path: Path, *, expected_sha256: str, commit: str) -> dict:
    if not COMMIT_RE.fullmatch(commit):
        raise DirectSolError("DIRECT_SOL_IMMUTABLE_COMMIT_REQUIRED")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise DirectSolError("DIRECT_SOL_PUBLICATION_HASH")
    request = validate_request(json.loads(raw))
    if not TASK_RE.fullmatch(request["task_id"]):
        raise DirectSolError("DIRECT_SOL_SAFE_TASK_ID_REQUIRED")
    if path.name != request["task_id"] + ".json":
        raise DirectSolError("DIRECT_SOL_REQUEST_FILENAME")
    return request


def context_for(request: dict, *, commit: str, request_sha256: str) -> str:
    validate_request(request)
    task_id = request["task_id"]
    if not TASK_RE.fullmatch(task_id) or not COMMIT_RE.fullmatch(commit):
        raise DirectSolError("DIRECT_SOL_REFERENCE_INVALID")
    if not re.fullmatch(r"[0-9a-f]{64}", request_sha256):
        raise DirectSolError("DIRECT_SOL_PUBLICATION_HASH")
    return (
        "PREDICTION_DIRECT_SOL_HANDOFF_V1\n"
        f"task_id={task_id}\n"
        "repository=bas1231/onderzoek\n"
        f"immutable_commit={commit}\n"
        f"request_path=control/model_execution/direct_requests/{task_id}.json\n"
        f"request_sha256={request_sha256}\n"
        f"input_sha256={request['input_sha256']}\n"
        f"binding_sha256={request['binding_sha256']}\n"
        f"worker_route_task_id={request['delivery_route_task_id']}\n"
        "This is the owner's authorized DIRECT_SOL handoff, not a model completion.\n"
        "Read the COMPLETE immutable request using the GitHub connector at exactly "
        "this commit before doing any model work. Do not reconstruct or shorten its prompt.\n"
        "Execute only if the actual platform-provided identity is EXACT GPT-5.6 Sol "
        "in regular Chat, work_mode=false and codex=false. The requested label, "
        "a route ID and your own assertion do not establish platform identity. "
        "If the runtime does not expose identity/experience, write a BLOCKED event "
        "with reason MODEL_IDENTITY_UNAVAILABLE; never impersonate the requested model. "
        "If this is not the exact routed chat, write BLOCKED_ROUTE_MISMATCH.\n"
        f"Worker events: control/model_execution/direct_worker_events/{task_id}/"
        "{STARTED,COMPLETE,BLOCKED}.json. Use immutable create-only GitHub writes. "
        "Include task_id, input_sha256, request_sha256, actual route, actual observed "
        "model/experience and their evidence source; use null for unavailable facts. "
        "Read existing result and events first. An existing COMPLETE/result means "
        "do not repeat inference. STARTED without completion means ambiguous prior "
        "execution: stop with BLOCKED_AMBIGUOUS_EXECUTION, do not silently retry.\n"
        "After full request retrieval and identity verification, create STARTED. "
        "Perform the governed prompt substantively. Publish the new "
        "PREDICTION_DIRECT_SOL_RESULT_V1 result at "
        f"control/model_execution/direct_results/{task_id}.json, "
        "with exact request metadata, your observed identity, actual timestamps, "
        "full final content and SHA-256 completion binding. Record actual provenance; "
        "do not invent times, hashes, tools or received model results. "
        "Then create COMPLETE referencing the immutable result commit.\n"
        "For this proposal no experiment build, code execution, tests or measurement. "
        "GitHub transport tools are allowed; no Codex/Work substitution, paid APIs, "
        "credential access, trades or wallets. NO_PROVEN_EDGE remains in force. "
        "Do not modify bridge components or create local executor tasks. "
        "After publishing a genuine result choose the existing continuation DONE "
        "receipt; on missing capability choose BLOCKED. Transport DONE alone is "
        "not lifecycle success. The controller will verify provenance before Astra PREBUILD.\n"
    )


def delivery_status(record: dict, *, model_result_present: bool, now: float,
                    created_at: float, deadline_seconds: int) -> str:
    if model_result_present:
        return "MODEL_RESULT_PRESENT_REQUIRES_VALIDATION"
    if record.get("state") in {
        "BLOCKED", "BLOCKED_TRANSPORT", "BLOCKED_RECEIPT_CREATED"
    }:
        return "BLOCKED_WORKER_OR_TRANSPORT"
    if now >= created_at + deadline_seconds:
        return "BLOCKED_NO_MODEL_RESULT"
    return "WAITING_FOR_ACTUAL_SOL_RESULT"


def enqueue_published_request(*, request_path: Path, request_sha256: str,
                              commit: str, bridge_data: Path, state_root: Path,
                              continuation, now: float | None = None,
                              deadline_seconds: int = 300) -> dict:
    request = published_request(request_path, expected_sha256=request_sha256, commit=commit)
    if type(deadline_seconds) is not int or not 30 <= deadline_seconds <= 1800:
        raise DirectSolError("DIRECT_SOL_DEADLINE_INVALID")
    context = context_for(request, commit=commit, request_sha256=request_sha256)
    route_id = request["delivery_route_task_id"]
    if not TASK_RE.fullmatch(route_id):
        raise DirectSolError("DIRECT_SOL_SAFE_ROUTE_REQUIRED")
    route = json.loads((bridge_data / "routes" / (route_id + ".json")).read_text())
    if route.get("task_id") != route_id or not re.fullmatch(
        r"[A-Za-z0-9._:-]{1,160}", str(route.get("chat_id", ""))
    ):
        raise DirectSolError("DIRECT_SOL_ROUTE_BINDING_INVALID")
    source_id = "DIRECT-SOL-" + request["task_id"]
    intent = {
        "schema": "PREDICTION_DIRECT_SOL_DELIVERY_INTENT_V1",
        "task_id": request["task_id"],
        "source_task_id": source_id,
        "publication_commit": commit,
        "request_sha256": request_sha256,
        "input_sha256": request["input_sha256"],
        "binding_sha256": request["binding_sha256"],
        "worker_route_task_id": route_id,
        "chat_id": route["chat_id"],
        "context_sha256": hashlib.sha256(context.encode()).hexdigest(),
        "deadline_seconds": deadline_seconds,
        "model_identity_status": "NOT_VERIFIED_BY_TRANSPORT",
    }
    folder = state_root / request["task_id"]
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except PermissionError as exc:
        raise DirectSolError("DIRECT_SOL_STATE_ROOT_NOT_WRITABLE") from exc
    with (folder / "dispatch.lock").open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        _immutable_json(folder / "INTENT.json", intent)
        try:
            record = continuation.start_external_continuation(
                data_dir=bridge_data, source_task_id=source_id, chat_id=route["chat_id"],
                expected_route_task_id=route_id, context_message=context,
                source_kind="DIRECT_SOL_GOVERNED_REQUEST",
            )
        except PermissionError as exc:
            raise DirectSolError("DIRECT_SOL_CONTINUATION_CAPABILITY_UNAVAILABLE") from exc
        current = time.time() if now is None else now
        created_at = float(record["created_at"])
        status = delivery_status(
            record, model_result_present=False, now=current, created_at=created_at,
            deadline_seconds=deadline_seconds,
        )
        queued = False
        if status == "WAITING_FOR_ACTUAL_SOL_RESULT":
            queued = continuation.enqueue_attempt(
                record=record, data_dir=bridge_data, routes_dir=bridge_data / "routes",
                outbox_dir=bridge_data / "outbox", now=current,
            )
        return {
            **intent, "continuation_id": record["continuation_id"],
            "continuation_state": record["state"], "new_delivery_queued": queued,
            "model_status": status, "model_execution_proven": False,
            "deadline_at": created_at + deadline_seconds,
        }
