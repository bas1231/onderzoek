#!/usr/bin/env python3
import argparse
import json
import os
import re
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HOME = Path.home()
DATA_DIR = HOME / ".local" / "share" / "prediction-chat-bridge"
OUTBOX = DATA_DIR / "outbox"
SENT = DATA_DIR / "sent"
ROUTES = DATA_DIR / "routes"
TOKEN_FILE = HOME / ".config" / "prediction-chat-bridge" / "token"
DEFAULT_CHAT_FILE = DATA_DIR / "default_chat.json"
USERSCRIPT_FILE = DATA_DIR / "prediction-chat-wake.user.js"

TASK_RE = re.compile(r"^[A-Za-z0-9._:-]{1,160}$")
CHAT_RE = re.compile(r"^[A-Za-z0-9._:-]{4,180}$")
CONSUMER_RE = re.compile(r"^[A-Za-z0-9._:-]{4,220}$")
LEASE_SECONDS = 45.0
LEASES = {}
LEASE_LOCK = threading.Lock()


def ensure_dirs():
    for p in (OUTBOX, SENT, ROUTES):
        p.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_token():
    token = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not token:
        raise RuntimeError(f"Empty token file: {TOKEN_FILE}")
    return token


def safe_id(value, regex):
    value = str(value or "").strip()
    return value if regex.fullmatch(value) else None


def route_for_task(task_id):
    task_id = str(task_id or "").strip()
    if not TASK_RE.fullmatch(task_id):
        return None
    path = ROUTES / f"{task_id}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return safe_id(data.get("chat_id"), CHAT_RE)


def default_chat():
    if not DEFAULT_CHAT_FILE.exists():
        return None
    try:
        data = json.loads(DEFAULT_CHAT_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None
    return safe_id(data.get("chat_id"), CHAT_RE)


def event_files():
    return sorted(OUTBOX.glob("*.json"), key=lambda p: (p.stat().st_mtime_ns, p.name))


def load_event(path):
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(obj, dict) or not obj.get("event_id"):
        return None
    return obj


def lease_available(event_id, chat_id, consumer_id):
    now = time.monotonic()
    with LEASE_LOCK:
        current = LEASES.get(event_id)
        if current and current[2] > now:
            return current[0] == chat_id and current[1] == consumer_id
        LEASES[event_id] = (chat_id, consumer_id, now + LEASE_SECONDS)
        return True


def release_lease(event_id):
    with LEASE_LOCK:
        LEASES.pop(event_id, None)


def oldest_event(chat_id=None, consumer_id=None):
    for path in event_files():
        obj = load_event(path)
        if obj is None:
            continue
        task_id = str(obj.get("task_id") or "")
        route = route_for_task(task_id)
        fallback = default_chat()

        if chat_id is None:
            # Backward compatibility during upgrade: a legacy v1 tab can still
            # consume unrouted work until a v3 fallback chat is registered.
            if route is not None or fallback is not None:
                continue
            return path, obj

        # Routed work returns only to the chat that created that task. Unrouted
        # autonomous wakeups go only to the explicitly selected fallback chat.
        if route != chat_id and not (route is None and fallback == chat_id):
            continue
        if not lease_available(str(obj["event_id"]), chat_id, consumer_id or chat_id):
            continue
        return path, obj

    return None, None


def json_bytes(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    server_version = "PredictionChatWake/0.3"

    def log_message(self, fmt, *args):
        if self.command != "GET" or not self.path.startswith("/next"):
            super().log_message(fmt, *args)

    def authorized(self):
        header = self.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return False
        return secrets.compare_digest(header[7:].strip(), self.server.bridge_token)

    def reply_json(self, status, obj):
        body = json_bytes(obj)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def reply_userscript(self):
        if not USERSCRIPT_FILE.exists():
            self.reply_json(404, {"ok": False, "error": "userscript_not_installed"})
            return
        body = USERSCRIPT_FILE.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/javascript; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)

        # Deliberately unauthenticated: loopback-only, contains no secret, and
        # lets Tampermonkey install/update the userscript directly in the browser.
        if parsed.path == "/prediction-chat-wake.user.js":
            self.reply_userscript()
            return

        if not self.authorized():
            self.reply_json(401, {"ok": False, "error": "unauthorized"})
            return

        if parsed.path == "/health":
            self.reply_json(200, {"ok": True, "service": "prediction-chat-wake", "version": 3, "multichat": True})
            return
        if parsed.path != "/next":
            self.reply_json(404, {"ok": False, "error": "not_found"})
            return

        qs = parse_qs(parsed.query)
        raw_chat = (qs.get("chat_id") or [""])[0]
        raw_consumer = (qs.get("consumer_id") or [""])[0]
        chat_id = safe_id(raw_chat, CHAT_RE) if raw_chat else None
        consumer_id = safe_id(raw_consumer, CONSUMER_RE) if raw_consumer else None

        if raw_chat and chat_id is None:
            self.reply_json(400, {"ok": False, "error": "bad_chat_id"})
            return
        if raw_consumer and consumer_id is None:
            self.reply_json(400, {"ok": False, "error": "bad_consumer_id"})
            return
        if chat_id and not consumer_id:
            self.reply_json(400, {"ok": False, "error": "consumer_id_required"})
            return

        deadline = time.monotonic() + 20.0
        while time.monotonic() < deadline:
            _, obj = oldest_event(chat_id, consumer_id)
            if obj is not None:
                self.reply_json(200, obj)
                return
            time.sleep(0.25)

        self.send_response(204)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        if not self.authorized():
            self.reply_json(401, {"ok": False, "error": "unauthorized"})
            return
        if parsed.path != "/ack":
            self.reply_json(404, {"ok": False, "error": "not_found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(min(length, 16384))
            payload = json.loads(body or b"{}")
        except Exception:
            self.reply_json(400, {"ok": False, "error": "bad_json"})
            return

        event_id = str(payload.get("event_id", ""))
        if not event_id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in event_id):
            self.reply_json(400, {"ok": False, "error": "bad_event_id"})
            return

        raw_chat = str(payload.get("chat_id", "") or "")
        raw_consumer = str(payload.get("consumer_id", "") or "")
        chat_id = safe_id(raw_chat, CHAT_RE) if raw_chat else None
        consumer_id = safe_id(raw_consumer, CONSUMER_RE) if raw_consumer else None
        if raw_chat and chat_id is None:
            self.reply_json(400, {"ok": False, "error": "bad_chat_id"})
            return
        if raw_consumer and consumer_id is None:
            self.reply_json(400, {"ok": False, "error": "bad_consumer_id"})
            return

        src = OUTBOX / f"{event_id}.json"
        dst = SENT / f"{event_id}.json"
        if src.exists():
            obj = load_event(src)
            if obj is None:
                self.reply_json(409, {"ok": False, "error": "invalid_event"})
                return

            route = route_for_task(str(obj.get("task_id") or ""))
            expected_chat = route or default_chat()
            if expected_chat is not None and chat_id != expected_chat:
                self.reply_json(409, {"ok": False, "error": "chat_mismatch"})
                return
            if expected_chat is None and chat_id is not None:
                self.reply_json(409, {"ok": False, "error": "unrouted_event"})
                return

            with LEASE_LOCK:
                lease = LEASES.get(event_id)
            if lease and lease[2] > time.monotonic():
                if chat_id is not None and lease[0] != chat_id:
                    self.reply_json(409, {"ok": False, "error": "chat_lease_mismatch"})
                    return
                if consumer_id is not None and lease[1] != consumer_id:
                    self.reply_json(409, {"ok": False, "error": "consumer_mismatch"})
                    return

            os.replace(src, dst)
            release_lease(event_id)
            self.reply_json(200, {"ok": True, "event_id": event_id})
            return

        if dst.exists():
            release_lease(event_id)
            self.reply_json(200, {"ok": True, "event_id": event_id, "already_acked": True})
            return

        self.reply_json(404, {"ok": False, "error": "event_not_found"})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    ensure_dirs()
    token = load_token()
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    httpd.daemon_threads = True
    httpd.bridge_token = token
    print(f"prediction-chat-wake v3 listening on http://{args.host}:{args.port}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
