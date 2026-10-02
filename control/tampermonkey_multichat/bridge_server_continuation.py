#!/usr/bin/env python3
"""Transactional auto-continuation overlay for PredictionChatWake.

This layer does not depend on Tampermonkey. It hooks the canonical wake ACK
boundary and emits continuation wake events through the same /next queue used
for ordinary results. Browser delivery is intentionally non-terminal; only
one durable command-bus outcome can close a continuation.
"""
from __future__ import annotations

import argparse
from http.server import ThreadingHTTPServer
from pathlib import Path

import bridge_server_status_compaction as current
import continuation_manager as continuation

base = current.base
TASK_STATE_DIR = Path.home() / ".local" / "state" / "prediction-command-bus" / "tasks"
_CURRENT_OLDEST_EVENT = base.oldest_event


def continuation_ack_hook(
    event: dict,
    *,
    chat_id: str | None,
    consumer_id: str | None,
    already_acked: bool,
) -> None:
    del consumer_id, already_acked

    # ACK of a continuation wake event means only that a browser agent observed
    # the corresponding ChatGPT user turn. It is not a downstream-success
    # receipt and must never consume the logical continuation.
    if continuation.mark_delivery_acked(data_dir=base.DATA_DIR, event=event):
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
    """Reconcile/reoffer only unresolved continuations for this chat."""
    if chat_id:
        continuation.maintain_for_chat(
            data_dir=base.DATA_DIR,
            task_state_dir=TASK_STATE_DIR,
            routes_dir=base.ROUTES,
            outbox_dir=base.OUTBOX,
            chat_id=str(chat_id),
        )
    return _CURRENT_OLDEST_EVENT(chat_id, consumer_id)


# bridge_server_v2.Handler resolves both globals at request time.
base.ACK_HOOK = continuation_ack_hook
base.oldest_event = continuation_oldest_event


class Handler(current.Handler):
    server_version = "PredictionChatWake/1.3-continuation-v2"


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
        f"prediction-chat-wake continuation-v2 listening "
        f"on http://{args.host}:{args.port}",
        flush=True,
    )
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
