#!/usr/bin/env python3
"""Consumer-resilient wake wrapper for same-chat result delivery.

A route's chat_id is the durable security/addressing boundary. A browser tab's
consumer_id is ephemeral and is suitable for an active lease, but must not
permanently pin a route: reloads or replacement tabs otherwise strand valid
results in OUTBOX forever.

This wrapper preserves session bootstrap, fail-closed inflight semantics in the
installed base module, nested-status-safe compaction and BRIDGE_PING status
handling. It only normalizes stored route bindings to chat scope at delivery
time; different chat_id values remain isolated.
"""
from __future__ import annotations

import argparse
import re
from http.server import ThreadingHTTPServer

import bridge_server_session_bootstrap as session

base = session.base
MAX_BROWSER_MESSAGE = session.hardened.MAX_BROWSER_MESSAGE

# Keep the original disk-backed route lookup exactly once, even if this module
# is imported repeatedly in a test/runtime process.
if not hasattr(base, "_prediction_chat_scoped_route_original"):
    base._prediction_chat_scoped_route_original = base.route_binding_for_task
_ORIGINAL_ROUTE_BINDING = base._prediction_chat_scoped_route_original


def chat_scoped_route_binding(task_id):
    """Return the stored route while dropping only the ephemeral tab binding."""
    binding = _ORIGINAL_ROUTE_BINDING(task_id)
    if not binding:
        return None
    chat_id = str(binding.get("chat_id") or "").strip()
    if not chat_id:
        return None
    return {"chat_id": chat_id, "consumer_id": None}


# bridge_server_v2.oldest_event and Handler.do_POST resolve this global at call
# time. Therefore both leasing and ACK keep chat isolation while allowing a
# refreshed/replacement tab in the same chat to continue delivery. The current
# consumer still owns the active in-memory lease.
base.route_binding_for_task = chat_scoped_route_binding


def _final_status(raw: str, exit_code: int | None) -> str:
    values = re.findall(r"DEV_TASK_STATUS=(PASS|FAIL)", raw)
    if values:
        return values[-1]
    if "BRIDGE_PONG" in raw and exit_code is not None:
        return "PASS" if exit_code == 0 else "FAIL"
    return "UNKNOWN"


def _outer_command_rcs(raw: str) -> list[str]:
    latest: dict[int, str] = {}
    for n, rc in re.findall(r"COMMAND_(\d+)_RC=(-?\d+)", raw):
        latest[int(n)] = rc
    out: list[str] = []
    idx = 1
    while idx in latest and len(out) < 20:
        out.append(f"{idx}:{latest[idx]}")
        idx += 1
    return out


def _clean_detail(value: str, limit: int = 320) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    return value[:limit]


def compact_delivery_event(obj):
    """Preserve the current compact browser result format."""
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
        exit_match = re.search(r"Exit code:\s*(-?\d+)", raw, re.I)
        exit_code = int(exit_match.group(1)) if exit_match else None
        status = _final_status(raw, exit_code)
        errors = re.findall(r"ERROR_CLASS=([^\r\n]+)", raw)
        details = re.findall(r"^ERROR=([^\r\n]+)", raw, re.M)
        rcs = _outer_command_rcs(raw)
        shas = re.findall(r"\b[0-9a-f]{40}\b", raw)

        parts = [
            "NIGHTSHIFT_WSL_RESULT_V1",
            f"task={task_id or 'UNKNOWN'}",
            f"status={status}",
        ]
        if exit_code is not None:
            parts.append(f"exit={exit_code}")
        if rcs:
            parts.append(f"rcs={','.join(rcs)}")
        if status == "FAIL":
            if errors:
                parts.append(f"error={_clean_detail(errors[-1], 120)}")
            if details:
                parts.append(f"detail={_clean_detail(details[-1])}")
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


session.hardened.compact_delivery_event = compact_delivery_event


class Handler(session.Handler):
    server_version = "PredictionChatWake/1.2-chat-scoped-route"


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
        f"prediction-chat-wake chat-scoped-route listening on http://{args.host}:{args.port}",
        flush=True,
    )
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
