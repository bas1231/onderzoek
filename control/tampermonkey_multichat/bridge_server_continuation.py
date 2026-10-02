#!/usr/bin/env python3
"""Transactional control-continuation overlay for the canonical wake bridge.

This layer does not change browser/Tampermonkey code. It reuses the existing
/next + /ack transport and treats browser ACK only as delivery evidence.
Durable success is derived from the existing command-bus task state.
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
_ORIGINAL_RELEASE_LEASE = base.release_lease


def _start_continuation_for_sent_event(event_id: str) -> None:
    sent = base.SENT / f"{event_id}.json"
    obj = base.load_event(sent)
    if not obj:
        return

    source_task_id = str(obj.get("task_id") or "").strip()
    if not source_task_id:
        return

    binding = base.route_binding_for_task(source_task_id)
    if not binding:
        return

    chat_id = str(binding.get("chat_id") or "").strip()
    if not chat_id:
        return

    continuation.start_for_result_ack(
        data_dir=base.DATA_DIR,
        task_state_dir=TASK_STATE_DIR,
        source_task_id=source_task_id,
        chat_id=chat_id,
    )


def continuation_release_lease(event_id: str) -> None:
    """Observe durable SENT after the existing ACK path releases its lease."""
    _ORIGINAL_RELEASE_LEASE(event_id)
    try:
        _start_continuation_for_sent_event(event_id)
    except Exception as exc:
        # Result ACK must remain authoritative even if continuation bookkeeping
        # fails. Fail closed by leaving no continuation rather than corrupting
        # the already-proven result delivery.
        print(
            f"continuation ack hook failed event={event_id} "
            f"error={type(exc).__name__}:{exc}",
            flush=True,
        )


def continuation_oldest_event(chat_id=None, consumer_id=None):
    """Reconcile/reoffer only unresolved continuations for this chat."""
    if chat_id:
        try:
            continuation.maintain_for_chat(
                data_dir=base.DATA_DIR,
                task_state_dir=TASK_STATE_DIR,
                routes_dir=base.ROUTES,
                outbox_dir=base.OUTBOX,
                chat_id=str(chat_id),
            )
        except Exception as exc:
            print(
                f"continuation maintenance failed chat={chat_id} "
                f"error={type(exc).__name__}:{exc}",
                flush=True,
            )
    return _CURRENT_OLDEST_EVENT(chat_id, consumer_id)


# bridge_server_v2.Handler resolves these module globals at request time.
# Replacing them composes with the existing inflight/session/bootstrap/status
# layers without duplicating their routing or ACK implementations.
base.release_lease = continuation_release_lease
base.oldest_event = continuation_oldest_event


class Handler(current.Handler):
    server_version = "PredictionChatWake/1.2-continuation-v2"


def main() -> int:
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
        f"prediction-chat-wake continuation-v2 listening "
        f"on http://{args.host}:{args.port}",
        flush=True,
    )
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
