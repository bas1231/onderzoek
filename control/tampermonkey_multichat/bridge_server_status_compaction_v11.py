#!/usr/bin/env python3
"""Browser-facing result compaction with explicit BRIDGE_PING status handling.

Preserves the E013 nested DEV receipt rules and adds one narrow rule for the
plain bridge health-check transport: BRIDGE_PONG + outer Exit code 0 is PASS;
BRIDGE_PONG + non-zero outer Exit code is FAIL. Other non-DEV wrappers remain
UNKNOWN rather than being promoted from exit code alone.
"""
from __future__ import annotations

import argparse
import re
from http.server import ThreadingHTTPServer

import bridge_server_session_bootstrap as session

base = session.base
MAX_BROWSER_MESSAGE = session.hardened.MAX_BROWSER_MESSAGE


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


def compact_delivery_event(obj):
    out = dict(obj)
    raw = str(obj.get("message") or "")
    task_id = str(obj.get("task_id") or "").strip()
    event_id = str(obj.get("event_id") or "").strip()

    if "PREDICTION_SNAPSHOT_EXPORT_V1" in raw:
        meta_match = re.search(r"^SNAPSHOT_EXPORT_META=(\{[^\r\n]+\})$", raw, re.M)
        data_match = re.search(r"^SNAPSHOT_EXPORT_DATA=([A-Za-z0-9+/=]+)$", raw, re.M)
        if not meta_match or not data_match:
            message = (
                "PREDICTION_SNAPSHOT_EXPORT_V1 "
                f"task={task_id or 'UNKNOWN'} status=FAIL reason=EXPORT_FIELDS_MISSING"
            )
        else:
            message = (
                "PREDICTION_SNAPSHOT_EXPORT_V1 "
                f"task={task_id or 'UNKNOWN'} "
                f"meta={meta_match.group(1)} data={data_match.group(1)}"
            )
        if len(message) > MAX_SNAPSHOT_EXPORT_MESSAGE:
            message = (
                "PREDICTION_SNAPSHOT_EXPORT_V1 "
                f"task={task_id or 'UNKNOWN'} status=FAIL reason=EXPORT_CHUNK_TOO_LARGE"
            )
        out["message"] = message
        out["delivery_compacted"] = True
        out["raw_message_bytes"] = len(raw.encode("utf-8", errors="replace"))
        out["snapshot_export_delivery"] = True
        return out

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


session.hardened.compact_delivery_event = compact_delivery_event


class Handler(session.Handler):
    server_version = "PredictionChatWake/1.1-bridge-ping-status"


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
        f"prediction-chat-wake bridge-ping-status listening on http://{args.host}:{args.port}",
        flush=True,
    )
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
