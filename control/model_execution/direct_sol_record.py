from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from control.model_execution.direct_sol_chat import (
    EXECUTION_LAYER,
    PROVENANCE_KIND,
    TARGET_DISPLAY,
    TARGET_EXPERIENCE,
    TARGET_MODEL,
    validate_request,
    validate_result,
)

PROVENANCE_SCHEMA = "PVA_DIRECT_SOL_CHAT_PROVENANCE_V1"


def _epoch(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def _sha(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def normalized_run_files(
    request: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, str]:
    validate_request(request)
    validate_result(request, result)

    started = _epoch(result["started_at_utc"])
    finished = _epoch(result["finished_at_utc"])
    if finished < started:
        raise ValueError("DIRECT_SOL_TIME_ORDER")

    task = {
        "task_id": request["task_id"],
        "task_class": "research_review",
        "prompt": request["prompt"],
        "input_sha256": request["input_sha256"],
        "model_policy": "SOL_EXACT",
        "route_task_id": request["delivery_route_task_id"],
        "campaign_id": request["campaign_id"],
        "candidate_id": request["candidate_id"],
        "phase": request["phase"],
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
    }
    worker = {
        "model": TARGET_MODEL,
        "model_selection": {
            "policy": "SOL_EXACT",
            "selected_slug": TARGET_MODEL,
            "display_name": TARGET_DISPLAY,
        },
        "thread_id": result["worker_route_task_id"],
        "started_at": started,
        "execution_layer": EXECUTION_LAYER,
        "experience": TARGET_EXPERIENCE,
        "provenance_kind": PROVENANCE_KIND,
        "worker_route_task_id": result["worker_route_task_id"],
        "command_flags": [],
    }
    complete = {
        "task_id": request["task_id"],
        "input_sha256": request["input_sha256"],
        "attempt": 1,
        "thread_id": result["worker_route_task_id"],
        "final": result["final"],
        "timestamp": finished,
    }
    events = [
        {"type": "thread.started", "thread_id": result["worker_route_task_id"]},
        {
            "type": "item.completed",
            "item": {"type": "agent_message", "text": result["final"]},
        },
        {"type": "turn.completed"},
    ]

    return {
        "TASK.json": json.dumps(task, sort_keys=True),
        "WORKER.json": json.dumps(worker, sort_keys=True),
        "COMPLETE.json": json.dumps(complete, sort_keys=True),
        "events.jsonl": "".join(json.dumps(e, sort_keys=True) + "\n" for e in events),
    }


def provenance_record(ref_prefix: str, files: dict[str, str]) -> dict[str, Any]:
    expected = {"TASK.json", "WORKER.json", "COMPLETE.json", "events.jsonl"}
    if set(files) != expected:
        raise ValueError("DIRECT_SOL_RUN_FILESET")
    return {
        "schema": PROVENANCE_SCHEMA,
        "revoked": False,
        "execution_layer": EXECUTION_LAYER,
        "provenance_kind": PROVENANCE_KIND,
        "files": {
            name: {
                "ref": ref_prefix.rstrip("/") + "/" + name,
                "sha256": _sha(files[name]),
            }
            for name in sorted(files)
        },
    }
