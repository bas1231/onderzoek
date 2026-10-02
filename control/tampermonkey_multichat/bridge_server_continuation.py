#!/usr/bin/env python3
"""Transactional auto-continuation overlay for PredictionChatWake.

This layer does not depend on Tampermonkey. It uses the canonical wake /next
and /ack transport. Browser delivery is intentionally non-terminal; only one
durable command-bus outcome can close a continuation.

Fresh runtimes use bridge_server_v2.ACK_HOOK. Older installed runtimes may
still contain the separately inflight-patched bridge_server_v2 from the
command-bus installer. For those runtimes this overlay provides a compatibility
hook through release_lease without replacing the inflight-patched base file.
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
_BASE_HAS_ACK_HOOK = hasattr(base, "ACK_HOOK")


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


def continuation_release_lease(event_id: str) -> None:
    """Compatibility ACK hook for installed inflight-patched base runtimes.

    bridge_server_v2 moves a newly ACKed event to SENT before release_lease.
    Duplicate ACKs also call release_lease while the SENT copy exists.  We load
    that durable event and invoke the same idempotent continuation hook.

    Deliberately do not swallow hook exceptions: an ACK-side bookkeeping
    failure must make the HTTP ACK fail so the browser agent retries. Because
    the event is already in SENT, the retry cannot redeliver the user message.
    """
    _ORIGINAL_RELEASE_LEASE(event_id)

    sent = base.SENT / f"{event_id}.json"
    event = base.load_event(sent)
    if not event:
        return

    task_id = str(event.get("task_id") or "").strip()
    binding = base.route_binding_for_task(task_id) if task_id else None
    chat_id = str(binding.get("chat_id") or "").strip() if binding else ""
    if not chat_id:
        return

    continuation_ack_hook(
        event,
        chat_id=chat_id,
        consumer_id=None,
        already_acked=True,
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


# Fresh source runtimes resolve ACK_HOOK at request time. Existing installed
# inflight runtimes predate ACK_HOOK, so compose through release_lease instead
# of overwriting their patched bridge_server_v2.py.
if _BASE_HAS_ACK_HOOK:
    base.ACK_HOOK = continuation_ack_hook
else:
    base.release_lease = continuation_release_lease

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
