#!/usr/bin/env python3
"""Result-status compaction overlay for the session-bootstrap wake bridge.

The DEV transport may intentionally print the receipt of an older task while
running a diagnostic.  Those nested receipts can contain their own
DEV_TASK_STATUS / ERROR_CLASS / COMMAND_*_RC markers.  The previous compactor
used the *first* status marker and therefore could report an outer PASS task as
FAIL when its output merely contained an older failed receipt.

This overlay keeps the existing routing/bootstrap/dedupe behaviour and only
changes browser-facing result compaction:
- final DEV_TASK_STATUS wins;
- outer transport Exit code stays the first wrapper-level Exit code marker;
- repeated COMMAND_n_RC markers keep the last value for that command index;
- ERROR_CLASS is emitted only when the final task status is FAIL.
"""
from __future__ import annotations

import argparse
import re
from http.server import ThreadingHTTPServer

import bridge_server_session_bootstrap as session

base = session.base
MAX_BROWSER_MESSAGE = session.hardened.MAX_BROWSER_MESSAGE


def _final_status(raw: str) -> str:
    values = re.findall(r"DEV_TASK_STATUS=(PASS|FAIL)", raw)
    return values[-1] if values else "UNKNOWN"


def _outer_command_rcs(raw: str) -> list[str]:
    """Return a compact best-effort outer RC view.

    Diagnostics can embed older receipts with duplicate command indices.  The
    real outer runner prints its own COMMAND_n_RC after command stdout, so the
    last occurrence for an index is authoritative.  Only the contiguous outer
    sequence beginning at command 1 is shown.
    """
    latest: dict[int, str] = {}
    for n, rc in re.findall(r"COMMAND_(\d+)_RC=(-?\d+)", raw):
        latest[int(n)] = rc
    out: list[str] = []
    idx = 1
    while idx in latest and len(out) < 20:
        out.append(f"{idx}:{latest[idx]}")
        idx += 1
    return out


def compact_delivery_event(obj):
    """Return a browser-safe event copy without trusting nested receipt status."""
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
        status = _final_status(raw)
        # RESULT_READY wrapper writes the authoritative process exit before the
        # captured WSL stdout.  Nested receipts may contain another Exit code.
        exit_match = re.search(r"Exit code:\s*(-?\d+)", raw, re.I)
        errors = re.findall(r"ERROR_CLASS=([^\r\n]+)", raw)
        rcs = _outer_command_rcs(raw)
        shas = re.findall(r"\b[0-9a-f]{40}\b", raw)

        parts = [
            "NIGHTSHIFT_WSL_RESULT_V1",
            f"task={task_id or 'UNKNOWN'}",
            f"status={status}",
        ]
        if exit_match:
            parts.append(f"exit={exit_match.group(1)}")
        if rcs:
            parts.append(f"rcs={','.join(rcs)}")
        if status == "FAIL" and errors:
            err = re.sub(r"\s+", " ", errors[-1]).strip()[:120]
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


# Hardened.Handler.reply_json resolves this global at request time.
session.hardened.compact_delivery_event = compact_delivery_event


class Handler(session.Handler):
    server_version = "PredictionChatWake/1.0-status-compaction"


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
        f"prediction-chat-wake status-compaction listening on http://{args.host}:{args.port}",
        flush=True,
    )
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
