#!/usr/bin/env python3
"""Active-page routing overlay for the Prediction chat command router.

The browser page reports presence with its existing authenticated chat_id and
consumer_id. Only a visible, focused page becomes the active command target.
An inactive report can clear only its own active binding. This gives the
GitHub command bus a direct page binding without SESSION_ROUTE bootstrap.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
from http.server import ThreadingHTTPServer
from pathlib import Path

try:
    import command_router_base as base
except ImportError:  # repository/unit-test mode
    import command_router as base

ACTIVE_PAGE_FILE = base.DATA_DIR / "active_page.json"
ACTIVE_PAGE_TTL_SECONDS = 8.0


def _atomic_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def read_active_page() -> dict | None:
    try:
        obj = json.loads(ACTIVE_PAGE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None


def update_presence(chat_id: str, consumer_id: str, focused: bool, visible: bool) -> dict:
    now = time.time()
    active = bool(focused and visible)
    current = read_active_page()
    if active:
        payload = {
            "version": 1,
            "active": True,
            "chat_id": chat_id,
            "consumer_id": consumer_id,
            "updated_at_unix": now,
            "source": "tampermonkey_focus_presence",
        }
        _atomic_json(ACTIVE_PAGE_FILE, payload)
        return payload

    # A background tab may never clear another foreground tab's binding.
    if isinstance(current, dict) and (
        str(current.get("chat_id") or "") == chat_id
        and str(current.get("consumer_id") or "") == consumer_id
    ):
        payload = dict(current)
        payload["active"] = False
        payload["updated_at_unix"] = now
        _atomic_json(ACTIVE_PAGE_FILE, payload)
        return payload
    return current or {
        "version": 1,
        "active": False,
        "chat_id": chat_id,
        "consumer_id": consumer_id,
        "updated_at_unix": now,
        "source": "tampermonkey_focus_presence",
    }


def active_page_status() -> dict:
    obj = read_active_page()
    if not isinstance(obj, dict):
        return {"fresh": False, "active": False}
    try:
        age = max(0.0, time.time() - float(obj.get("updated_at_unix", 0.0)))
    except Exception:
        age = 10**9
    return {
        "fresh": bool(obj.get("active") is True and age <= ACTIVE_PAGE_TTL_SECONDS),
        "active": bool(obj.get("active") is True),
        "age_seconds": round(age, 3),
        "chat_id": str(obj.get("chat_id") or ""),
        "consumer_id": str(obj.get("consumer_id") or ""),
    }


class Handler(base.Handler):
    server_version = "PredictionChatCommandRouter/0.3-active-page"

    def do_GET(self):
        if self.path == "/health":
            if not self.authorized():
                self.reply(401, {"ok": False, "error": "unauthorized"})
                return
            self.reply(200, {
                "ok": True,
                "service": "prediction-chat-command-router",
                "version": 3,
                "upstream_port": 8766,
                "consumer_routing": True,
                "active_page_routing": True,
                "active_page_ttl_seconds": ACTIVE_PAGE_TTL_SECONDS,
                "active_page": active_page_status(),
            })
            return
        super().do_GET()

    def do_POST(self):
        if self.path != "/presence":
            super().do_POST()
            return
        if not self.authorized():
            self.reply(401, {"ok": False, "error": "unauthorized"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 8192:
                self.reply(413 if length > 8192 else 400, {"ok": False, "error": "bad_length"})
                return
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError("truncated body")
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("payload must be object")
        except Exception:
            self.reply(400, {"ok": False, "error": "bad_json"})
            return

        chat_id = str(payload.get("chat_id") or "").strip()
        consumer_id = str(payload.get("consumer_id") or "").strip()
        if not base.CHAT_RE.fullmatch(chat_id):
            self.reply(400, {"ok": False, "error": "bad_chat_id"})
            return
        if not base.CONSUMER_RE.fullmatch(consumer_id):
            self.reply(400, {"ok": False, "error": "bad_consumer_id"})
            return
        focused = payload.get("focused") is True
        visible = payload.get("visible") is True
        state = update_presence(chat_id, consumer_id, focused, visible)
        self.reply(200, {
            "ok": True,
            "active": bool(state.get("active") is True),
            "chat_id": chat_id,
            "consumer_id": consumer_id,
        })


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8767)
    args = parser.parse_args()
    base.ensure_dirs()
    token = base.load_token()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.daemon_threads = True
    server.bridge_token = token
    print(f"prediction-chat-command-router active-page listening on http://{args.host}:{args.port}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
