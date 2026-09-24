#!/usr/bin/env python3
"""Hardened wrapper around bridge_server_v2.

Delivery invariants are enforced at the localhost boundary, independent of which
Tampermonkey script version is currently installed:

1. /next never exposes unbounded RESULT_READY/WSL stdout to the browser.
2. Once any event for a task_id is in SENT, later OUTBOX events for that same
   task_id are silently retired and never delivered again.
3. The dedicated nightshift userscript is served from loopback for install/update.
4. Nightshift heartbeat can be generated server-side for one explicitly bound
   chat, so an old-but-working browser userscript can keep the session moving.

The server-side heartbeat is intentionally opt-in, bounded by an expiry time,
and tells the assistant to continue only while the agreed nightshift task is
unfinished. Once that task is complete, later heartbeats must be ignored and
must not start new work.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import threading
import time
from http.server import ThreadingHTTPServer

import bridge_server_v2 as base

MAX_BROWSER_MESSAGE = 900
HEARTBEAT_MESSAGE = (
    "ga door. Als de afgesproken nightshift-taak volledig is afgerond, "
    "negeer deze heartbeat en start niets nieuws."
)
NIGHTSHIFT_USERSCRIPT_FILE = base.DATA_DIR / "prediction-nightshift-wake.user.js"
NIGHTSHIFT_MODE_FILE = base.DATA_DIR / "nightshift_mode.json"
_RAW_OLDEST_EVENT = base.oldest_event
_HEARTBEAT_LOCK = threading.Lock()


def _atomic_json(path, obj) -> None:
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    os.replace(tmp, path)


def _load_mode() -> dict | None:
    if not NIGHTSHIFT_MODE_FILE.exists():
        return None
    try:
        mode = json.loads(NIGHTSHIFT_MODE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(mode, dict) or mode.get("enabled") is not True:
        return None
    chat_id = base.safe_id(mode.get("chat_id"), base.CHAT_RE)
    if not chat_id:
        return None
    try:
        expires_at = float(mode.get("expires_at") or 0)
    except Exception:
        return None
    if expires_at <= time.time():
        return None
    return mode


def _heartbeat_interval(mode: dict) -> float:
    try:
        value = float(mode.get("interval_seconds") or 300.0)
    except Exception:
        value = 300.0
    return min(300.0, max(15.0, value))


def _maybe_enqueue_heartbeat(chat_id) -> bool:
    """Create one routed heartbeat event when nightshift mode is due."""
    if not chat_id:
        return False

    with _HEARTBEAT_LOCK:
        mode = _load_mode()
        if not mode or str(mode.get("chat_id")) != str(chat_id):
            return False

        now = time.time()
        try:
            not_before = float(mode.get("not_before") or 0)
            last_emit_at = float(mode.get("last_emit_at") or 0)
        except Exception:
            return False
        if now < not_before:
            return False
        if (now - last_emit_at) < _heartbeat_interval(mode):
            return False

        token = secrets.token_hex(4)
        epoch_ms = int(now * 1000)
        task_id = f"DEV-PRED-NIGHTSHIFT-HEARTBEAT-{epoch_ms}-{token}"
        event_id = f"hb-{epoch_ms}-{token}"
        route_path = base.ROUTES / f"{task_id}.json"
        event_path = base.OUTBOX / f"{event_id}.json"

        _atomic_json(route_path, {
            "task_id": task_id,
            "chat_id": str(chat_id),
            "source": "server_heartbeat",
            "created_at": now,
        })
        _atomic_json(event_path, {
            "event_id": event_id,
            "task_id": task_id,
            "message": HEARTBEAT_MESSAGE,
            "created_at": now,
            "source": "server_heartbeat",
        })

        mode["last_emit_at"] = now
        mode["last_event_id"] = event_id
        _atomic_json(NIGHTSHIFT_MODE_FILE, mode)
        return True


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
    """Return the first not-yet-delivered task event, then heartbeat if due."""
    for _ in range(256):
        path, obj = _RAW_OLDEST_EVENT(chat_id, consumer_id)
        if obj is None:
            if _maybe_enqueue_heartbeat(chat_id):
                continue
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
    server_version = "PredictionChatWake/0.7-hardened"

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
            mode = _load_mode()
            self.reply_json(200, {
                "ok": True,
                "service": "prediction-chat-wake",
                "version": 7,
                "multichat": True,
                "server_compaction": True,
                "task_dedupe": True,
                "server_heartbeat": True,
                "heartbeat_mode_enabled": bool(mode),
                "heartbeat_interval_seconds": _heartbeat_interval(mode) if mode else None,
                "heartbeat_done_guard": True,
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