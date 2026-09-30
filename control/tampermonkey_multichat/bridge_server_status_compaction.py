#!/usr/bin/env python3
"""Result-status compaction overlay for the session-bootstrap wake bridge.

The DEV transport may intentionally print the receipt of an older task while
running a diagnostic. Nested receipts can contain their own DEV_TASK_STATUS,
ERROR_CLASS, ERROR and COMMAND_*_RC markers. The compactor therefore treats
the final outer status as authoritative while surfacing the final concrete
ERROR detail only for an outer FAIL.
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
    """Return a compact best-effort outer RC view."""
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
    """Return a browser-safe event copy with authoritative outer status/error."""
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
        exit_match = re.search(r"Exit code:\s*(-?\d+)", raw, re.I)
        errors = re.findall(r"ERROR_CLASS=([^\r\n]+)", raw)
        details = re.findall(r"^ERROR=([^\r\n]+)", raw, re.M)
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
    server_version = "PredictionChatWake/1.1-error-detail"


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
        f"prediction-chat-wake error-detail listening on http://{args.host}:{args.port}",
        flush=True,
    )
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
