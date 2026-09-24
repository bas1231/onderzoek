#!/usr/bin/env python3
import argparse
import json
import os
import re
import secrets
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

HOME = Path.home()
DATA_DIR = HOME / ".local" / "share" / "prediction-chat-bridge"
ROUTES = DATA_DIR / "routes"
TOKEN_FILE = HOME / ".config" / "prediction-chat-bridge" / "token"
DEFAULT_CHAT_FILE = DATA_DIR / "default_chat.json"
UPSTREAM = "http://127.0.0.1:8766/command"

TASK_RE = re.compile(r"^[A-Za-z0-9._:-]{1,160}$")
CHAT_RE = re.compile(r"^[A-Za-z0-9._:-]{4,180}$")
CONSUMER_RE = re.compile(r"^[A-Za-z0-9._:-]{4,220}$")


def ensure_dirs():
    ROUTES.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_token():
    value = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not value:
        raise RuntimeError(f"Empty token file: {TOKEN_FILE}")
    return value


def json_bytes(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def read_route(task_id):
    path = ROUTES / f"{task_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_route(task_id, chat_id, consumer_id=None):
    path = ROUTES / f"{task_id}.json"
    payload = {
        "version": 2,
        "task_id": task_id,
        "chat_id": chat_id,
        "consumer_id": consumer_id,
        "created_at_unix": time.time(),
    }
    encoded = (json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        existing = read_route(task_id)
        old_chat = str((existing or {}).get("chat_id") or "")
        old_consumer = str((existing or {}).get("consumer_id") or "")
        if old_chat and old_chat != chat_id:
            raise ValueError("TASK_ROUTE_CONFLICT")
        # Existing legacy routes stay chat-scoped. For consumer-aware routes,
        # a second tab may not claim the same task_id.
        if old_consumer and consumer_id and old_consumer != consumer_id:
            raise ValueError("TASK_ROUTE_CONFLICT")
        return existing or payload

    try:
        with os.fdopen(fd, "wb") as f:
            f.write(encoded)
            f.flush()
            os.fsync(f.fileno())
    except Exception:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise
    return payload


def write_default_chat(chat_id):
    payload = {"version": 1, "chat_id": chat_id, "updated_at_unix": time.time()}
    fd, tmp_name = tempfile.mkstemp(prefix=".default_chat.", suffix=".tmp", dir=str(DATA_DIR))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, DEFAULT_CHAT_FILE)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
    return payload


def forward_command(payload, token):
    body = json_bytes({"action": payload["action"], "task_id": payload["task_id"]})
    req = Request(
        UPSTREAM,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=15) as resp:
            raw = resp.read(65536)
            status = resp.status
    except HTTPError as exc:
        raw = exc.read(65536)
        status = exc.code
    except URLError as exc:
        return 503, {"ok": False, "error": "upstream_unreachable", "detail": str(exc.reason)}

    try:
        data = json.loads(raw or b"{}")
    except Exception:
        data = {"ok": 200 <= status < 300, "raw": raw.decode("utf-8", errors="replace")}
    return status, data


class Handler(BaseHTTPRequestHandler):
    server_version = "PredictionChatCommandRouter/0.2"

    def log_message(self, fmt, *args):
        if self.path != "/health":
            super().log_message(fmt, *args)

    def authorized(self):
        header = self.headers.get("Authorization", "")
        return header.startswith("Bearer ") and secrets.compare_digest(header[7:].strip(), self.server.bridge_token)

    def reply(self, status, obj):
        body = json_bytes(obj)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self.authorized():
            self.reply(401, {"ok": False, "error": "unauthorized"})
            return
        if self.path == "/health":
            self.reply(200, {
                "ok": True,
                "service": "prediction-chat-command-router",
                "version": 2,
                "upstream_port": 8766,
                "consumer_routing": True,
            })
            return
        self.reply(404, {"ok": False, "error": "not_found"})

    def do_POST(self):
        if not self.authorized():
            self.reply(401, {"ok": False, "error": "unauthorized"})
            return
        if self.path not in {"/command", "/fallback"}:
            self.reply(404, {"ok": False, "error": "not_found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(min(length, 32768)) or b"{}")
        except Exception:
            self.reply(400, {"ok": False, "error": "bad_json"})
            return

        chat_id = str(payload.get("chat_id") or "").strip()
        if not CHAT_RE.fullmatch(chat_id):
            self.reply(400, {"ok": False, "error": "bad_chat_id"})
            return
        if self.path == "/fallback":
            write_default_chat(chat_id)
            self.reply(200, {"ok": True, "chat_id": chat_id, "fallback": True})
            return

        task_id = str(payload.get("task_id") or "").strip()
        action = str(payload.get("action") or "").strip()
        raw_consumer = str(payload.get("consumer_id") or "").strip()
        consumer_id = raw_consumer or None
        if not TASK_RE.fullmatch(task_id):
            self.reply(400, {"ok": False, "error": "bad_task_id"})
            return
        if not action or len(action) > 80:
            self.reply(400, {"ok": False, "error": "bad_action"})
            return
        if raw_consumer and not CONSUMER_RE.fullmatch(raw_consumer):
            self.reply(400, {"ok": False, "error": "bad_consumer_id"})
            return

        try:
            route = write_route(task_id, chat_id, consumer_id)
        except ValueError:
            self.reply(409, {"ok": False, "error": "TASK_ROUTE_CONFLICT", "task_id": task_id})
            return

        status, result = forward_command({"action": action, "task_id": task_id}, self.server.bridge_token)
        if isinstance(result, dict):
            result = dict(result)
            result.setdefault("chat_id", chat_id)
            result.setdefault("consumer_id", (route or {}).get("consumer_id"))
            result.setdefault("routed", True)
        self.reply(status, result)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8767)
    args = parser.parse_args()
    ensure_dirs()
    token = load_token()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.daemon_threads = True
    server.bridge_token = token
    print(f"prediction-chat-command-router listening on http://{args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
