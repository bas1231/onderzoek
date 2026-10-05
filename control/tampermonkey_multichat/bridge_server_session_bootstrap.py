#!/usr/bin/env python3
"""Automatic same-chat route bootstrap layered on the hardened wake bridge.

A current Prediction Chat Wake userscript already polls /next with a stable
chat_id + consumer_id.  That is enough to bootstrap routing without scanning
assistant DOM output.  For a chat that has no previously ACKed routed result,
this wrapper creates a chat-scoped route and a small idempotent control event:

  NIGHTSHIFT_WSL_RESULT_V1 task=SESSION-ROUTE-... status=PASS exit=0 kind=SESSION_ROUTE_BOOTSTRAP

Once that event is ACKed it is itself a proven route_task_id for the session.
No command is executed to create the route.  Ambiguous bootstrap delivery may
be re-announced after a bounded delay because the announcement is idempotent;
command execution remains at-most-once and is not retried here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import time
import re
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import bridge_server_hardened as hardened

base = hardened.base
_HARDENED_OLDEST_EVENT = hardened.hardened_oldest_event
SESSION_PREFIX = "SESSION-ROUTE-"
SESSION_EVENT_PREFIX = "session-route-"
REANNOUNCE_AFTER_SECONDS = 90.0
MAX_SCAN_FILES = 4096
DASHBOARD_LAUNCH_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{16,96}$")
DASHBOARD_LAUNCHER_TTL_SECONDS = 180.0


def _dashboard_launchers_dir() -> Path:
    return base.DATA_DIR / "dashboard_launchers"


def _dashboard_launches_dir() -> Path:
    return base.DATA_DIR / "dashboard_launches"


def _validate_launch_base_url(value: str) -> str | None:
    try:
        parsed = urlparse(str(value or "").strip())
    except Exception:
        return None
    if parsed.scheme != "https" or parsed.netloc != "chatgpt.com":
        return None
    if parsed.query or parsed.fragment:
        return None
    path = parsed.path.rstrip("/")
    if not path or path == "/" or "/c/" in path:
        return None
    return f"https://chatgpt.com{path}"


def register_dashboard_launcher(payload: dict) -> dict:
    chat = base.safe_id(payload.get("chat_id"), base.CHAT_RE)
    consumer = base.safe_id(payload.get("consumer_id"), base.CONSUMER_RE)
    launch_base_url = _validate_launch_base_url(payload.get("launch_base_url"))
    script_version = str(payload.get("script_version") or "")[:64]
    if not chat or not consumer or not launch_base_url:
        raise ValueError("BAD_DASHBOARD_LAUNCHER")
    key = hashlib.sha256(f"{chat}|{consumer}".encode("utf-8")).hexdigest()[:32]
    record = {
        "schema": "PREDICTION_DASHBOARD_LAUNCHER_V1",
        "chat_id": chat,
        "consumer_id": consumer,
        "launch_base_url": launch_base_url,
        "script_version": script_version,
        "updated_at_unix": time.time(),
        "capabilities": ["dashboard_new_session_launch_v1"],
    }
    _atomic_json(_dashboard_launchers_dir() / f"{key}.json", record)
    return record


def load_dashboard_launch(token: str) -> dict | None:
    if not DASHBOARD_LAUNCH_TOKEN_RE.fullmatch(str(token or "")):
        return None
    path = _dashboard_launches_dir() / f"{token}.json"
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(obj, dict) or obj.get("schema") != "PREDICTION_DASHBOARD_CHAT_LAUNCH_V1":
        return None
    return obj


def acknowledge_dashboard_launch(token: str) -> dict:
    obj = load_dashboard_launch(token)
    if obj is None:
        raise KeyError(token)
    updated = dict(obj)
    updated["state"] = "PROMPT_SUBMITTED"
    updated["submitted_at_unix"] = time.time()
    _atomic_json(_dashboard_launches_dir() / f"{token}.json", updated)
    return updated



def _atomic_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _session_task_id(chat_id: str) -> str:
    digest = hashlib.sha256(chat_id.encode("utf-8")).hexdigest()[:24]
    return f"{SESSION_PREFIX}{digest}"


def _route_chat(task_id: str) -> str | None:
    binding = base.route_binding_for_task(task_id)
    return str(binding.get("chat_id")) if binding else None


def _iter_events(directory: Path):
    try:
        paths = list(directory.glob("*.json"))
    except OSError:
        return
    paths.sort(key=lambda p: p.stat().st_mtime_ns if p.exists() else 0, reverse=True)
    for path in paths[:MAX_SCAN_FILES]:
        obj = base.load_event(path)
        if obj:
            yield path, obj


def _chat_has_proven_route(chat_id: str) -> bool:
    """A SENT event with a matching route is proof this chat received a task."""
    for _, obj in _iter_events(base.SENT):
        task_id = str(obj.get("task_id") or "").strip()
        if task_id and _route_chat(task_id) == chat_id:
            return True
    return False


def _ensure_route_file(task_id: str, chat_id: str) -> None:
    path = base.ROUTES / f"{task_id}.json"
    if path.exists():
        binding = base.route_binding_for_task(task_id)
        if not binding or str(binding.get("chat_id") or "") != chat_id:
            raise RuntimeError("SESSION_ROUTE_CONFLICT")
        return
    _atomic_json(path, {
        "version": 2,
        "task_id": task_id,
        "chat_id": chat_id,
        "consumer_id": None,
        "source": "auto_session_bootstrap",
        "created_at_unix": time.time(),
    })


def _task_events(task_id: str):
    directories = [base.OUTBOX, getattr(base, "INFLIGHT", base.DATA_DIR / "inflight"), base.SENT]
    for directory in directories:
        for path, obj in _iter_events(directory):
            if str(obj.get("task_id") or "") == task_id:
                yield directory, path, obj


def _enqueue_announcement(task_id: str) -> bool:
    now = time.time()
    seen_outbox = False
    newest_inflight = None
    for directory, path, _ in _task_events(task_id):
        if directory == base.SENT:
            return False
        if directory == base.OUTBOX:
            seen_outbox = True
        else:
            try:
                age = now - path.stat().st_mtime
            except OSError:
                age = 0.0
            if newest_inflight is None or age < newest_inflight:
                newest_inflight = age
    if seen_outbox:
        return False
    if newest_inflight is not None and newest_inflight < REANNOUNCE_AFTER_SECONDS:
        return False

    token = secrets.token_hex(4)
    event_id = f"{SESSION_EVENT_PREFIX}{int(now * 1000)}-{token}"
    message = (
        f"NIGHTSHIFT_WSL_RESULT_V1 task={task_id} status=PASS exit=0 "
        "kind=SESSION_ROUTE_BOOTSTRAP"
    )
    _atomic_json(base.OUTBOX / f"{event_id}.json", {
        "event_id": event_id,
        "task_id": task_id,
        "message": message,
        "created_at": now,
        "source": "auto_session_bootstrap",
    })
    return True


def ensure_session_bootstrap(chat_id: str | None, consumer_id: str | None) -> str | None:
    """Ensure a route announcement exists for a stable consumer-aware chat."""
    chat = base.safe_id(chat_id, base.CHAT_RE) if chat_id else None
    consumer = base.safe_id(consumer_id, base.CONSUMER_RE) if consumer_id else None
    if not chat or not consumer:
        return None
    if _chat_has_proven_route(chat):
        return None
    task_id = _session_task_id(chat)
    _ensure_route_file(task_id, chat)
    _enqueue_announcement(task_id)
    return task_id


def session_oldest_event(chat_id=None, consumer_id=None):
    ensure_session_bootstrap(chat_id, consumer_id)
    return _HARDENED_OLDEST_EVENT(chat_id, consumer_id)


# The base Handler resolves oldest_event from bridge_server_v2 globals at
# request time, so this single assignment inserts bootstrap before the existing
# hardened compaction/dedupe/heartbeat path without changing its ACK logic.
base.oldest_event = session_oldest_event


class Handler(hardened.Handler):
    server_version = "PredictionChatWake/1.0-dashboard-new-session"

    def _read_json_body(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None
        if length < 1 or length > 65536:
            return None
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            return None

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path not in {"/dashboard-launcher/register", "/dashboard-launch/ack"}:
            return super().do_POST()
        if not self.authorized():
            self.reply_json(401, {"ok": False, "error": "unauthorized"})
            return
        payload = self._read_json_body()
        if not isinstance(payload, dict):
            self.reply_json(400, {"ok": False, "error": "bad_json"})
            return
        if parsed.path == "/dashboard-launcher/register":
            try:
                record = register_dashboard_launcher(payload)
            except ValueError:
                self.reply_json(400, {"ok": False, "error": "bad_launcher"})
                return
            self.reply_json(200, {"ok": True, "launcher": record})
            return
        token = str(payload.get("token") or "")
        try:
            updated = acknowledge_dashboard_launch(token)
        except KeyError:
            self.reply_json(404, {"ok": False, "error": "launch_not_found"})
            return
        self.reply_json(200, {
            "ok": True,
            "token": token,
            "state": updated.get("state"),
        })

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/dashboard-launch":
            if not self.authorized():
                self.reply_json(401, {"ok": False, "error": "unauthorized"})
                return
            token = (parse_qs(parsed.query).get("token") or [""])[0]
            launch = load_dashboard_launch(token)
            if launch is None:
                self.reply_json(404, {"ok": False, "error": "launch_not_found"})
                return
            self.reply_json(200, {
                "ok": True,
                "token": token,
                "request_id": launch.get("request_id"),
                "action": launch.get("action"),
                "work_item_id": launch.get("work_item_id"),
                "prompt": launch.get("prompt"),
                "state": launch.get("state"),
            })
            return
        if parsed.path == "/health":
            if not self.authorized():
                self.reply_json(401, {"ok": False, "error": "unauthorized"})
                return
            mode = hardened._load_mode()
            self.reply_json(200, {
                "ok": True,
                "service": "prediction-chat-wake",
                "version": 10,
                "multichat": True,
                "server_compaction": True,
                "task_dedupe": True,
                "server_heartbeat": True,
                "auto_session_bootstrap": True,
                "dashboard_new_session_launch": True,
                "dashboard_launcher_ttl_seconds": DASHBOARD_LAUNCHER_TTL_SECONDS,
                "session_bootstrap_transport": "wake_next",
                "session_bootstrap_requires_dom_scan": False,
                "session_bootstrap_reannounce_seconds": REANNOUNCE_AFTER_SECONDS,
                "heartbeat_mode_enabled": bool(mode),
                "heartbeat_interval_seconds": hardened._heartbeat_interval(mode) if mode else None,
                "heartbeat_done_guard": True,
                "heartbeat_inactivity_reset": True,
                "heartbeat_resets_on_bridge_result": True,
                "heartbeat_resets_on_assistant_command": True,
                "max_browser_message": hardened.MAX_BROWSER_MESSAGE,
                "nightshift_userscript": hardened.NIGHTSHIFT_USERSCRIPT_FILE.exists(),
            })
            return
        super().do_GET()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    base.ensure_dirs()
    _dashboard_launchers_dir().mkdir(parents=True, exist_ok=True)
    _dashboard_launches_dir().mkdir(parents=True, exist_ok=True)
    token = base.load_token()
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    httpd.daemon_threads = True
    httpd.bridge_token = token
    print(f"prediction-chat-wake dashboard-new-session listening on http://{args.host}:{args.port}", flush=True)
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
