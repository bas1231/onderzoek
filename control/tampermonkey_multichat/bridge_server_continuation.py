#!/usr/bin/env python3
"""Transactional control-continuation overlay for the canonical wake bridge.

This layer does not depend on Tampermonkey. It reuses the canonical /next +
/ack wake transport. Browser ACK is delivery evidence only; durable success is
derived from deterministic command-bus outcome task state.
"""
from __future__ import annotations

import argparse
from http.server import ThreadingHTTPServer
from pathlib import Path

import bridge_server_status_compaction as current
import continuation_manager as continuation

base = current.base
TASK_STATE_DIR = (
    Path.home()
    / ".local"
    / "state"
    / "prediction-command-bus"
    / "tasks"
)
_CURRENT_OLDEST_EVENT = base.oldest_event


def continuation_ack_hook(
    event: dict,
    *,
    chat_id: str | None,
    consumer_id: str | None,
    already_acked: bool,
) -> None:
    del consumer_id, already_acked

    # ACK of a continuation wake proves only delivery as a real browser user
    # turn. It must never consume the logical continuation.
    if continuation.mark_delivery_acked(
        data_dir=base.DATA_DIR,
        event=event,
    ):
        return

    source_task_id = str(event.get("task_id") or "").strip()
    if not source_task_id or not chat_id:
        return

    continuation.start_for_result_ack(
        data_dir=base.DATA_DIR,
        task_state_dir=TASK_STATE_DIR,
        source_task_id=source_task_id,
        chat_id=str(chat_id),
    )


def continuation_oldest_event(chat_id=None, consumer_id=None):
    """Reconcile/reoffer unresolved continuations before serving /next."""
    if chat_id:
        continuation.maintain_for_chat(
            data_dir=base.DATA_DIR,
            task_state_dir=TASK_STATE_DIR,
            routes_dir=base.ROUTES,
            outbox_dir=base.OUTBOX,
            chat_id=str(chat_id),
        )
    return _CURRENT_OLDEST_EVENT(chat_id, consumer_id)


# bridge_server_v2 resolves these globals at request time. This composes with
# the existing inflight/session/bootstrap/status layers without duplicating
# their routing or ACK implementation.
base.ACK_HOOK = continuation_ack_hook
base.oldest_event = continuation_oldest_event


class Handler(current.Handler):
    server_version = "PredictionChatWake/1.2-continuation-v2"

    def do_GET(self):
        from urllib.parse import urlparse

        parsed = urlparse(self.path)
        if parsed.path == "/health":
            if not self.authorized():
                self.reply_json(401, {"ok": False, "error": "unauthorized"})
                return
            self.reply_json(200, {
                "ok": True,
                "service": "prediction-chat-wake",
                "version": 12,
                "server_compaction": True,
                "task_dedupe": True,
                "auto_session_bootstrap": True,
                "transactional_continuation": True,
                "continuation_browser_ack_terminal": False,
                "continuation_max_attempts": continuation.MAX_ATTEMPTS,
                "continuation_retry_after_seconds": continuation.RETRY_AFTER_SECONDS,
            })
            return
        super().do_GET()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    base.ensure_dirs()
    continuation.continuation_dir(base.DATA_DIR).mkdir(parents=True, exist_ok=True)
    token = base.load_token()
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    httpd.daemon_threads = True
    httpd.bridge_token = token
    print(
        "prediction-chat-wake continuation-v2 listening "
        f"on http://{args.host}:{args.port}",
        flush=True,
    )
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
