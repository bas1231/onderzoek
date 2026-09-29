#!/usr/bin/env python3
"""Read-only GitHub -> localhost Prediction command bus.

Safety model:
- never writes to GitHub;
- never touches ~/prediction_research_prod working tree;
- durable local claim before localhost dispatch (at-most-once / fail closed);
- no automatic retry after an ambiguous dispatch;
- hard-block live trading, paid actions and wallet actions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

HOME = Path.home()
BUS_HOME = HOME / ".local" / "share" / "prediction-command-bus"
REPO = BUS_HOME / "repo"
STATE = HOME / ".local" / "state" / "prediction-command-bus"
TASK_STATE = STATE / "tasks"
INCIDENTS = STATE / "incidents"
CONFIG = HOME / ".config" / "prediction-command-bus"
ROUTE_FILE = CONFIG / "route.json"
TOKEN_FILE = HOME / ".config" / "prediction-chat-bridge" / "token"
BRIDGE_DATA = HOME / ".local" / "share" / "prediction-chat-bridge"
ROUTES = BRIDGE_DATA / "routes"
ROUTER_URL = "http://127.0.0.1:8767/command"
HEALTH_URL = "http://127.0.0.1:8767/health"
INBOX_PREFIX = "control/bridge_commands/inbox/"
SCHEMA = "PREDICTION_BRIDGE_COMMAND_V1"
TASK_RE = re.compile(r"^[A-Za-z0-9._:-]{1,160}$")
ACTION_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,79}$")
ID_RE = re.compile(r"^[A-Za-z0-9._:-]{4,220}$")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def ensure_dirs() -> None:
    for p in (BUS_HOME, STATE, TASK_STATE, INCIDENTS, CONFIG):
        p.mkdir(parents=True, exist_ok=True)


def atomic_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, sort_keys=True, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(REPO), *args],
        check=check,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def fetch_remote() -> str:
    if not (REPO / ".git").exists():
        raise RuntimeError(f"BUS_REPO_NOT_INITIALIZED:{REPO}")
    git("fetch", "--quiet", "--depth=1", "origin", "main")
    return git("rev-parse", "FETCH_HEAD").stdout.strip()


def list_inbox_paths() -> list[str]:
    cp = git("ls-tree", "-r", "--name-only", "FETCH_HEAD", "--", "control/bridge_commands/inbox")
    return sorted(
        p.strip()
        for p in cp.stdout.splitlines()
        if p.strip().startswith(INBOX_PREFIX) and p.strip().endswith(".json")
    )


def remote_bytes(path: str) -> bytes:
    cp = subprocess.run(
        ["git", "-C", str(REPO), "show", f"FETCH_HEAD:{path}"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return cp.stdout


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def task_state_path(task_id: str) -> Path:
    return TASK_STATE / f"{task_id}.json"


def load_json(path: Path) -> dict | None:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def incident(code: str, detail: dict) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    payload = {"schema": "PREDICTION_COMMAND_BUS_INCIDENT_V1", "code": code, "at_utc": utc_now(), **detail}
    atomic_json(INCIDENTS / f"{stamp}-{code}.json", payload)


def validate_command(obj: dict) -> tuple[bool, str]:
    required = {
        "schema", "task_id", "action", "created_at_utc", "live_trading",
        "paid_actions", "wallet_actions", "intelligence_tier", "issuer",
    }
    allowed = required | {"route_task_id", "notes"}
    if set(obj) - allowed:
        return False, "UNKNOWN_FIELDS"
    if not required.issubset(obj):
        return False, "MISSING_FIELDS"
    if obj.get("schema") != SCHEMA:
        return False, "BAD_SCHEMA"
    if not TASK_RE.fullmatch(str(obj.get("task_id") or "")):
        return False, "BAD_TASK_ID"
    if not ACTION_RE.fullmatch(str(obj.get("action") or "")):
        return False, "BAD_ACTION"
    if obj.get("live_trading") is not False:
        return False, "LIVE_TRADING_BLOCKED"
    if obj.get("paid_actions") is not False:
        return False, "PAID_ACTIONS_BLOCKED"
    if obj.get("wallet_actions") is not False:
        return False, "WALLET_ACTIONS_BLOCKED"
    if obj.get("intelligence_tier") not in {"A", "B", "C"}:
        return False, "BAD_INTELLIGENCE_TIER"
    issuer = obj.get("issuer")
    if not isinstance(issuer, dict) or set(issuer) != {"model", "reasoning_level"}:
        return False, "BAD_ISSUER"
    if not str(issuer.get("model") or "").strip() or not str(issuer.get("reasoning_level") or "").strip():
        return False, "BAD_ISSUER"
    route_task_id = obj.get("route_task_id")
    if route_task_id is not None and not TASK_RE.fullmatch(str(route_task_id)):
        return False, "BAD_ROUTE_TASK_ID"
    if not isinstance(obj.get("created_at_utc"), str) or not obj["created_at_utc"].strip():
        return False, "BAD_CREATED_AT"
    if "notes" in obj and not isinstance(obj["notes"], str):
        return False, "BAD_NOTES"
    return True, "OK"


def validate_route(route: dict | None) -> dict | None:
    if not isinstance(route, dict):
        return None
    chat_id = str(route.get("chat_id") or "").strip()
    consumer_id = str(route.get("consumer_id") or "").strip()
    if not ID_RE.fullmatch(chat_id):
        return None
    if consumer_id and not ID_RE.fullmatch(consumer_id):
        return None
    return {"chat_id": chat_id, "consumer_id": consumer_id or None}


def resolve_route(command: dict) -> tuple[dict | None, str]:
    route_task_id = command.get("route_task_id")
    if route_task_id:
        path = ROUTES / f"{route_task_id}.json"
        route = validate_route(load_json(path))
        return route, f"task:{route_task_id}"
    route = validate_route(load_json(ROUTE_FILE))
    return route, "pinned"


def load_token() -> str:
    token = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not token:
        raise RuntimeError("EMPTY_BRIDGE_TOKEN")
    return token


def dispatch(command: dict, route: dict, token: str) -> tuple[str, int | None, str]:
    payload = {
        "action": command["action"],
        "task_id": command["task_id"],
        "chat_id": route["chat_id"],
    }
    if route.get("consumer_id"):
        payload["consumer_id"] = route["consumer_id"]
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    req = Request(
        ROUTER_URL,
        data=body,
        method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read(65536)
            return "RESPONSE", resp.status, raw.decode("utf-8", errors="replace")
    except HTTPError as exc:
        raw = exc.read(65536)
        return "HTTP_ERROR", exc.code, raw.decode("utf-8", errors="replace")
    except (URLError, OSError, TimeoutError) as exc:
        return "TRANSPORT_ERROR", None, f"{type(exc).__name__}:{exc}"


def process_one(path: str, remote_commit: str, token: str) -> str:
    raw = remote_bytes(path)
    content_sha = sha256(raw)
    try:
        obj = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        incident("BAD_JSON", {"path": path, "remote_commit": remote_commit, "detail": type(exc).__name__})
        return "BAD_JSON"
    if not isinstance(obj, dict):
        incident("BAD_ENVELOPE", {"path": path, "remote_commit": remote_commit})
        return "BAD_ENVELOPE"

    task_id = str(obj.get("task_id") or "")
    if not TASK_RE.fullmatch(task_id):
        incident("BAD_TASK_ID", {"path": path, "remote_commit": remote_commit, "content_sha256": content_sha})
        return "BAD_TASK_ID"

    state_path = task_state_path(task_id)
    existing = load_json(state_path)
    if existing is not None:
        if existing.get("content_sha256") != content_sha:
            incident("TASK_ID_CONTENT_CONFLICT", {
                "task_id": task_id,
                "path": path,
                "remote_commit": remote_commit,
                "old_content_sha256": existing.get("content_sha256"),
                "new_content_sha256": content_sha,
            })
            return "CONFLICT"
        return "ALREADY_CLAIMED"

    ok, reason = validate_command(obj)
    if not ok:
        record = {
            "schema": "PREDICTION_COMMAND_BUS_TASK_STATE_V1",
            "task_id": task_id,
            "status": "REJECTED",
            "reason": reason,
            "path": path,
            "remote_commit": remote_commit,
            "content_sha256": content_sha,
            "recorded_at_utc": utc_now(),
        }
        atomic_json(state_path, record)
        incident(reason, record)
        return "REJECTED"

    route, route_source = resolve_route(obj)
    if route is None:
        record = {
            "schema": "PREDICTION_COMMAND_BUS_TASK_STATE_V1",
            "task_id": task_id,
            "status": "BLOCKED_ROUTE",
            "path": path,
            "remote_commit": remote_commit,
            "content_sha256": content_sha,
            "route_source": route_source,
            "recorded_at_utc": utc_now(),
        }
        atomic_json(state_path, record)
        incident("BLOCKED_ROUTE", record)
        return "BLOCKED_ROUTE"

    claim = {
        "schema": "PREDICTION_COMMAND_BUS_TASK_STATE_V1",
        "task_id": task_id,
        "status": "CLAIMED",
        "action": obj["action"],
        "intelligence_tier": obj["intelligence_tier"],
        "issuer": obj["issuer"],
        "path": path,
        "remote_commit": remote_commit,
        "content_sha256": content_sha,
        "route_source": route_source,
        "chat_id": route["chat_id"],
        "consumer_id": route.get("consumer_id"),
        "claimed_at_utc": utc_now(),
    }
    atomic_json(state_path, claim)

    kind, http_status, response = dispatch(obj, route, token)
    final = dict(claim)
    final["completed_at_utc"] = utc_now()
    final["http_status"] = http_status
    final["response"] = response[:8192]

    if kind == "RESPONSE" and http_status is not None and 200 <= http_status < 300:
        try:
            envelope = json.loads(response or "{}")
        except Exception:
            envelope = None
        if isinstance(envelope, dict) and envelope.get("ok") is True:
            final["status"] = "DISPATCHED"
            atomic_json(state_path, final)
            return "DISPATCHED"
        final["status"] = "AMBIGUOUS"
        final["reason"] = "SUCCESS_STATUS_WITHOUT_OK_TRUE"
        atomic_json(state_path, final)
        incident("AMBIGUOUS_DISPATCH", final)
        return "AMBIGUOUS"

    if kind == "HTTP_ERROR":
        final["status"] = "REJECTED"
        final["reason"] = "LOCAL_ROUTER_REJECTED"
        atomic_json(state_path, final)
        incident("LOCAL_ROUTER_REJECTED", final)
        return "REJECTED"

    final["status"] = "AMBIGUOUS"
    final["reason"] = "LOCAL_TRANSPORT_AMBIGUOUS"
    atomic_json(state_path, final)
    incident("AMBIGUOUS_DISPATCH", final)
    return "AMBIGUOUS"


def router_health(token: str) -> dict:
    req = Request(HEALTH_URL, headers={"Authorization": f"Bearer {token}"})
    with urlopen(req, timeout=5) as resp:
        obj = json.loads(resp.read().decode("utf-8"))
    if not isinstance(obj, dict) or obj.get("ok") is not True:
        raise RuntimeError("ROUTER_HEALTH_NOT_OK")
    return obj


def run_once() -> int:
    ensure_dirs()
    token = load_token()
    health = router_health(token)
    remote_commit = fetch_remote()
    counts: dict[str, int] = {}
    for path in list_inbox_paths():
        result = process_one(path, remote_commit, token)
        counts[result] = counts.get(result, 0) + 1
    print(json.dumps({
        "ok": True,
        "remote_commit": remote_commit,
        "router_version": health.get("version"),
        "counts": counts,
        "at_utc": utc_now(),
    }, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="poll once; default behavior")
    args = parser.parse_args()
    try:
        return run_once()
    except Exception as exc:
        ensure_dirs()
        incident("POLLER_FATAL", {"detail": f"{type(exc).__name__}:{exc}"})
        print(json.dumps({"ok": False, "error": type(exc).__name__, "detail": str(exc)}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
