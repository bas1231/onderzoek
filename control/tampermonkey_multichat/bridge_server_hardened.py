#!/usr/bin/env python3
"""Hardened wrapper around bridge_server_v2.

Three invariants are enforced at the localhost delivery boundary, independent of
which Tampermonkey script is installed:

1. /next never exposes unbounded RESULT_READY/WSL stdout to the browser.
2. Once any event for a task_id is in SENT, later OUTBOX events for that same
   task_id are silently retired and never delivered again.
3. The dedicated nightshift userscript is served from loopback for a one-click
   Tampermonkey install/update without exposing bridge secrets.

This makes browser-side dedupe a second line of defence instead of the only one.
"""
from __future__ import annotations

import argparse
import os
import re
from http.server import ThreadingHTTPServer

import bridge_server_v2 as base

MAX_BROWSER_MESSAGE = 900
NIGHTSHIFT_USERSCRIPT_FILE = base.DATA_DIR / "prediction-nightshift-wake.user.js"
_RAW_OLDEST_EVENT = base.oldest_event


def _sent_task_ids() -> set[str]:
    seen: set[str] = set()
    for path in base.SENT.glob("*.json"):
        obj = base.load_event(path)
        if not obj:
            continue
        task_id = str(obj.get("task_id") or "").strip()
        if task_id:
            seen.add(task_id)
    return seen


def _retire_duplicate(path, obj) -> None:
    event_id = str(obj.get("event_id") or "")
    dst = base.SENT / path.name
    try:
        if dst.exists():
            path.unlink(missing_ok=True)
        else:
            os.replace(path, dst)
    finally:
        if event_id:
            base.release_lease(event_id)


def hardened_oldest_event(chat_id=None, consumer_id=None):
    """Return only the first not-yet-delivered task event."""
    for _ in range(256):
        path, obj = _RAW_OLDEST_EVENT(chat_id, consumer_id)
        if obj is None:
            return path, obj
        task_id = str(obj.get("task_id") or "").strip()
        if task_id and task_id in _sent_task_ids():
            _retire_duplicate(path, obj)
            continue
        return path, obj
    return None, None


def compact_delivery_event(obj):
    """Return a browser-safe event copy; raw event on disk remains untouched."""
    out = dict(obj)
    raw = str(obj.get("message") or "")
    task_id = str(obj.get("task_id") or "").strip()
    event_id = str(obj.get("event_id") or "").strip()

    looks_like_wsl = (
        raw.startswith("RESULT_READY:")
        or "=== WSL RESULT ===" in raw
        or "DEV_TASK_STATUS=" in raw
        or "BRIDGE_RESULT:" in raw
    )

    if looks_like_wsl:
        status_match = re.search(r"DEV_TASK_STATUS=(PASS|FAIL)", raw)
        exit_match = re.search(r"Exit code:\s*(-?\d+)", raw, re.I)
        error_match = re.search(r"ERROR_CLASS=([^\r\n]+)", raw)
        rcs = [f"{n}:{rc}" for n, rc in re.findall(r"COMMAND_(\d+)_RC=(-?\d+)", raw)]
        shas = re.findall(r"\b[0-9a-f]{40}\b", raw)

        parts = [
            "NIGHTSHIFT_WSL_RESULT_V1",
            f"task={task_id or 'UNKNOWN'}",
            f"status={status_match.group(1) if status_match else 'UNKNOWN'}",
        ]
        if exit_match:
            parts.append(f"exit={exit_match.group(1)}")
        if rcs:
            parts.append(f"rcs={','.join(rcs[:20])}")
        if error_match:
            err = re.sub(r"\s+", " ", error_match.group(1)).strip()[:120]
            parts.append(f"error={err}")
        if shas:
            parts.append(f"head={shas[-1]}")
        if event_id:
            parts.append(f"event={event_id[:80]}")
        message = " ".join(parts)
    else:
        message = raw

    if len(message) > MAX_BROWSER_MESSAGE:
        message = message[: MAX_BROWSER_MESSAGE - 22] + "...[SERVER_TRUNCATED]"

    out["message"] = message
    out["delivery_compacted"] = True
    out["raw_message_bytes"] = len(raw.encode("utf-8", errors="replace"))
    return out


base.oldest_event = hardened_oldest_event


class Handler(base.Handler):
    server_version = "PredictionChatWake/0.5-hardened"

    def reply_json(self, status, obj):
        if (
            status == 200
            and isinstance(obj, dict)
            and obj.get("event_id")
            and "message" in obj
        ):
            obj = compact_delivery_event(obj)
        super().reply_json(status, obj)

    def reply_nightshift_userscript(self):
        if not NIGHTSHIFT_USERSCRIPT_FILE.exists():
            self.reply_json(404, {"ok": False, "error": "nightshift_userscript_not_installed"})
            return
        body = NIGHTSHIFT_USERSCRIPT_FILE.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/javascript; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        from urllib.parse import urlparse
        parsed = urlparse(self.path)

        # Deliberately unauthenticated: loopback-only and contains no token.
        if parsed.path == "/prediction-nightshift-wake.user.js":
            self.reply_nightshift_userscript()
            return

        if parsed.path == "/health":
            if not self.authorized():
                self.reply_json(401, {"ok": False, "error": "unauthorized"})
                return
            self.reply_json(200, {
                "ok": True,
                "service": "prediction-chat-wake",
                "version": 5,
                "multichat": True,
                "server_compaction": True,
                "task_dedupe": True,
                "max_browser_message": MAX_BROWSER_MESSAGE,
                "nightshift_userscript": NIGHTSHIFT_USERSCRIPT_FILE.exists(),
            })
            return
        super().do_GET()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    base.ensure_dirs()
    token = base.load_token()
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    httpd.daemon_threads = True
    httpd.bridge_token = token
    print(
        f"prediction-chat-wake hardened listening on http://{args.host}:{args.port}",
        flush=True,
    )
    httpd.serve_forever()


if __name__ == "__main__":
    main()
