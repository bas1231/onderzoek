from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from control.model_execution.direct_sol_chat import TARGET_MODEL, validate_request, validate_result
from control.model_execution.direct_sol_record import normalized_run_files


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("DIRECT_SOL_JSON_OBJECT_REQUIRED")
    return value


def _immutable_text(path: Path, text: str) -> None:
    raw = text.encode("utf-8")
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError("DIRECT_SOL_RUNTIME_CONFLICT:" + str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(raw)


def _immutable_json(path: Path, value: dict[str, Any]) -> None:
    _immutable_text(path, json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def materialize(request_path: Path, result_path: Path, runtime: Path) -> dict[str, Any]:
    request_path = request_path.resolve()
    result_path = result_path.resolve()
    runtime = runtime.resolve()

    request = _json(request_path)
    result = _json(result_path)
    validate_request(request)
    validate_result(request, result)

    files = normalized_run_files(request, result)
    result_hash = _sha_bytes(result_path.read_bytes())
    folder = runtime / "models" / "runs" / (
        request["task_id"] + "-direct-" + result_hash[:12]
    )
    for name, text in files.items():
        _immutable_text(folder / name, text)

    complete_sha = _sha_bytes((folder / "COMPLETE.json").read_bytes())
    worker_sha = _sha_bytes((folder / "WORKER.json").read_bytes())
    envelope = {
        "schema": "PVA_GOVERNED_MODEL_COMPLETION_V1",
        "task_id": request["task_id"],
        "phase": request["phase"],
        "model": TARGET_MODEL,
        "model_policy": "SOL_EXACT",
        "execution_layer": "DIRECT_SOL_CHAT",
        "route_task_id": request["delivery_route_task_id"],
        "campaign_id": request["campaign_id"],
        "input_sha256": request["input_sha256"],
        "checkpoint": str(folder.relative_to(runtime)),
        "completion_sha256": complete_sha,
        "worker_sha256": worker_sha,
        "request_sha256": _sha_bytes(request_path.read_bytes()),
        "direct_result_sha256": result_hash,
        "final": result["final"],
    }
    out = runtime / "model_results" / (request["task_id"] + ".json")
    _immutable_json(out, envelope)
    return envelope
