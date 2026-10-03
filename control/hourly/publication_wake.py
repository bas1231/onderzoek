"""Bounded ChatGPT/GitHub publication handoff for compact durable research artifacts."""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import zlib

ROOT = Path(__file__).resolve().parents[2]
BRIDGE_DATA = Path.home() / ".local/share/prediction-chat-bridge"
ROUTE_CONFIG = BRIDGE_DATA / "autobuild_control_route.json"
ROUTES = BRIDGE_DATA / "routes"
AUDIT_ROOT = Path.home() / ".local/state/prediction-research/publication-wakes"
ROUTE_SCHEMA = "PREDICTION_AUTOBUILD_ROUTE_V1"
TASK_RE = re.compile(r"^[A-Za-z0-9._:-]{1,160}$")
CHAT_RE = re.compile(r"^[A-Za-z0-9._:-]{4,180}$")
MAX_CONTEXT = 6000
MAX_ENCODED_PAYLOAD = 4300


class PublicationBlocked(RuntimeError):
    pass


def _load_json(path: Path, reason: str) -> dict:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise PublicationBlocked(reason) from exc
    if not isinstance(obj, dict):
        raise PublicationBlocked(reason)
    return obj


def _load_continuation():
    path = ROOT / "control/tampermonkey_multichat/continuation_manager.py"
    spec = importlib.util.spec_from_file_location("prediction_publication_continuation", path)
    if spec is None or spec.loader is None:
        raise PublicationBlocked("CONTINUATION_UNAVAILABLE")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _control_route() -> tuple[str, str]:
    config = _load_json(ROUTE_CONFIG, "ROUTE_CONFIG_INVALID")
    if config.get("schema") != ROUTE_SCHEMA:
        raise PublicationBlocked("ROUTE_SCHEMA_INVALID")
    route_task_id = str(config.get("route_task_id") or "").strip()
    if not TASK_RE.fullmatch(route_task_id):
        raise PublicationBlocked("ROUTE_TASK_INVALID")
    route = _load_json(ROUTES / f"{route_task_id}.json", "ROUTE_BINDING_INVALID")
    chat_id = str(route.get("chat_id") or "").strip()
    if not CHAT_RE.fullmatch(chat_id):
        raise PublicationBlocked("CHAT_ROUTE_INVALID")
    return route_task_id, chat_id


def package(path: str, data: bytes) -> dict:
    digest = hashlib.sha256(data).hexdigest()
    encoded = base64.b64encode(zlib.compress(data, 9)).decode("ascii")
    return {
        "path": path,
        "sha256": digest,
        "bytes": len(data),
        "encoding": "zlib+base64",
        "payload": encoded,
        "publishable": len(encoded) <= MAX_ENCODED_PAYLOAD,
    }


def ensure_publication(path: str, *, root: Path = ROOT) -> dict:
    rel = Path(path).as_posix()
    target = (root / rel).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise PublicationBlocked("PATH_OUTSIDE_ROOT") from exc
    if not target.is_file():
        raise PublicationBlocked("SOURCE_MISSING")

    item = package(rel, target.read_bytes())
    if not item["publishable"]:
        return {
            "status": "OVERSIZED_LOCAL_ONLY",
            "path": rel,
            "sha256": item["sha256"],
            "bytes": item["bytes"],
            "encoded_bytes": len(item["payload"]),
        }

    route_task_id, chat_id = _control_route()
    source_task_id = "PUBLISH-" + hashlib.sha256(
        (rel + "\0" + item["sha256"]).encode("utf-8")
    ).hexdigest()[:40]
    context = (
        "PREDICTION_GITHUB_PUBLICATION_V1\n"
        "repository=bas1231/onderzoek\n"
        f"path={rel}\n"
        f"sha256={item['sha256']}\n"
        f"bytes={item['bytes']}\n"
        "encoding=zlib+base64\n"
        f"payload={item['payload']}\n"
        "safety=live_trading:false,paid_actions:false,wallet_actions:false,remote_git_write_via_wsl:false\n"
        "Decode exactly this bounded payload. Compare the current canonical GitHub file at the exact path. "
        "If it already has this SHA-256 choose DONE. Otherwise create/update exactly this one file via the GitHub connector, "
        "preserving the decoded bytes exactly; do not alter any other path. Then choose DONE. "
        "If exact publication is unsafe, ambiguous, or conflicts with newer canonical content, choose BLOCKED."
    )
    if len(context) > MAX_CONTEXT:
        raise PublicationBlocked("CONTEXT_LIMIT")

    continuation = _load_continuation()
    ids = continuation.ids_for(source_task_id)
    record_path = continuation.continuation_path(BRIDGE_DATA, ids["continuation_id"])
    existed_before = record_path.exists()
    record = continuation.start_external_continuation(
        data_dir=BRIDGE_DATA,
        source_task_id=source_task_id,
        chat_id=chat_id,
        expected_route_task_id=route_task_id,
        context_message=context,
        source_kind="GITHUB_PUBLICATION",
    )

    AUDIT_ROOT.mkdir(parents=True, exist_ok=True)
    audit = {
        "schema": "PREDICTION_GITHUB_PUBLICATION_WAKE_V1",
        "path": rel,
        "sha256": item["sha256"],
        "bytes": item["bytes"],
        "encoded_bytes": len(item["payload"]),
        "source_task_id": source_task_id,
        "continuation_id": record["continuation_id"],
        "route_task_id": route_task_id,
        "chat_id_sha256": hashlib.sha256(chat_id.encode("utf-8")).hexdigest(),
        "remote_push": False,
    }
    audit_path = AUDIT_ROOT / f"{source_task_id}.json"
    if audit_path.exists():
        if _load_json(audit_path, "AUDIT_INVALID") != audit:
            raise PublicationBlocked("AUDIT_CONFLICT")
    else:
        tmp = audit_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(audit_path)

    return {
        "status": "CONTINUATION_CREATED",
        "path": rel,
        "sha256": item["sha256"],
        "bytes": item["bytes"],
        "continuation_id": record["continuation_id"],
        "continuation_state": record["state"],
        "source_task_id": source_task_id,
        "new_continuation": not existed_before,
    }
