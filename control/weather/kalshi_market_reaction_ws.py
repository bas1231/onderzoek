#!/usr/bin/env python3
"""Authenticated *read-only* Kalshi WebSocket capture for KWI reaction research.

The authenticated handshake is required by Kalshi even for public market-data
channels. This program only subscribes to orderbook_delta and trade. It contains
no order/write endpoint. Credentials are read from environment/path and never
printed.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
from datetime import datetime, timezone
import inspect
import json
import os
from pathlib import Path
import time
from typing import Any

from market_reaction import OrderBook

WS_URL = "wss://external-api-ws.kalshi.com/trade-api/ws/v2"
WS_PATH = "/trade-api/ws/v2"
HOME = Path.home()
STATE = HOME / ".local" / "state" / "prediction-research"
LOGS = STATE / "kalshi_market_reaction_logs"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_event(fp, obj):
    fp.write(json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n")
    fp.flush()


def load_auth():
    key_id = os.environ.get("KALSHI_API_KEY_ID")
    key_path = os.environ.get("KALSHI_PRIVATE_KEY_PATH")
    if not key_id or not key_path:
        raise RuntimeError("read-only WS credentials unavailable: set KALSHI_API_KEY_ID and KALSHI_PRIVATE_KEY_PATH")
    p = Path(key_path).expanduser()
    if not p.is_file():
        raise RuntimeError("KALSHI_PRIVATE_KEY_PATH does not point to a file")
    try:
        from cryptography.hazmat.primitives import serialization
    except ImportError as exc:
        raise RuntimeError("cryptography package required for WS handshake") from exc
    with p.open("rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)
    return key_id, private_key


def auth_headers(key_id, private_key):
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    timestamp = str(int(time.time() * 1000))
    text = timestamp + "GET" + WS_PATH
    sig = private_key.sign(
        text.encode("utf-8"),
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
        hashes.SHA256(),
    )
    return {
        "KALSHI-ACCESS-KEY": key_id,
        "KALSHI-ACCESS-SIGNATURE": base64.b64encode(sig).decode("ascii"),
        "KALSHI-ACCESS-TIMESTAMP": timestamp,
    }


def validate_subscription_sequence(last_seq_by_sid: dict[int, int], msg: dict[str, Any]) -> None:
    sid = msg.get("sid")
    seq = msg.get("seq")
    typ = msg.get("type")
    if typ in ("orderbook_snapshot", "orderbook_delta") and (not isinstance(sid, int) or not isinstance(seq, int)):
        raise ValueError("orderbook frame missing sid/seq")
    if not isinstance(sid, int) or not isinstance(seq, int):
        return
    previous = last_seq_by_sid.get(sid)
    if previous is not None and seq != previous + 1:
        raise ValueError(f"subscription sequence gap sid={sid}: {previous}->{seq}")
    last_seq_by_sid[sid] = seq


def handle_message(books: dict[str, OrderBook], msg: dict[str, Any], recv_at: str, fp, last_seq_by_sid: dict[int, int]) -> None:
    """Persist one decoded WS frame and update reconstructed books fail-closed.

    Every successfully decoded frame is also transport coverage. This matters
    because a busy socket may never hit the recv timeout used for idle
    heartbeats; without this marker, valid capture could be misclassified as
    stale merely because messages kept arriving.
    """
    append_event(fp, {
        "kind": "coverage", "retrieved_at": recv_at, "transport": "ws",
    })
    append_event(fp, {
        "kind": "ws_raw", "retrieved_at": recv_at,
        "type": msg.get("type"), "sid": msg.get("sid"), "seq": msg.get("seq"),
        "msg": msg.get("msg"),
    })

    typ = msg.get("type")
    try:
        validate_subscription_sequence(last_seq_by_sid, msg)
    except ValueError as exc:
        append_event(fp, {
            "kind": "capture_gap", "start": recv_at, "end": recv_at,
            "reason": f"subscription_sequence:{str(exc)[:200]}", "transport": "ws",
        })
        raise
    if typ == "orderbook_snapshot":
        ticker = (msg.get("msg") or {}).get("market_ticker")
        if ticker in books:
            try:
                state = books[ticker].snapshot(msg, recv_at)
                append_event(fp, {"kind": "market_state", "retrieved_at": recv_at, **state.as_json()})
            except Exception as exc:
                append_event(fp, {
                    "kind": "capture_gap", "ticker": ticker,
                    "start": recv_at, "end": recv_at,
                    "reason": f"snapshot_reconstruction:{type(exc).__name__}:{str(exc)[:200]}",
                })
                # A malformed replacement snapshot can partially mutate a book.
                # Never keep trusting it; require a fresh valid snapshot.
                books[ticker] = OrderBook(ticker)
    elif typ == "orderbook_delta":
        ticker = (msg.get("msg") or {}).get("market_ticker")
        if ticker in books:
            try:
                state = books[ticker].delta(msg, recv_at)
                append_event(fp, {"kind": "market_state", "retrieved_at": recv_at, **state.as_json()})
            except Exception as exc:
                append_event(fp, {
                    "kind": "capture_gap", "ticker": ticker,
                    "start": recv_at, "end": recv_at,
                    "reason": f"delta_reconstruction:{type(exc).__name__}:{str(exc)[:200]}",
                })
                # Never continue trusting a book after a broken sequence/delta.
                books[ticker] = OrderBook(ticker)
    elif typ == "trade":
        append_event(fp, {
            "kind": "trade", "retrieved_at": recv_at,
            **(msg.get("msg") or {}),
        })
    elif typ == "error":
        append_event(fp, {
            "kind": "capture_error", "stage": "ws_server",
            "start": recv_at, "end": recv_at,
            "error_type": "KalshiWebSocketError",
            "error": str(msg.get("msg"))[:500],
        })


async def run_once(
    tickers: list[str],
    fp,
    duration_sec: float,
    *,
    reconnect_gap_start: str | None = None,
    connection_state: dict[str, bool] | None = None,
) -> None:
    try:
        import websockets
    except ImportError as exc:
        raise RuntimeError("websockets package required") from exc

    key_id, private_key = load_auth()
    headers = auth_headers(key_id, private_key)
    books = {t: OrderBook(t) for t in tickers}
    last_seq_by_sid: dict[int, int] = {}
    start = time.monotonic()

    # websockets >= 14 uses additional_headers; older releases use extra_headers.
    params = inspect.signature(websockets.connect).parameters
    header_kw = "additional_headers" if "additional_headers" in params else "extra_headers"
    ws_cm = websockets.connect(WS_URL, **{header_kw: headers})

    async with ws_cm as ws:
        connected_at = now_iso()
        if connection_state is not None:
            connection_state["connected"] = True
        if reconnect_gap_start is not None:
            append_event(fp, {
                "kind": "capture_gap", "start": reconnect_gap_start,
                "end": connected_at, "reason": "ws_reconnect_interval",
                "transport": "ws",
            })
        append_event(fp, {
            "kind": "ws_connected", "retrieved_at": connected_at,
            "tickers": tickers, "credential_material_logged": False,
        })
        append_event(fp, {"kind": "coverage", "retrieved_at": connected_at, "transport": "ws"})
        await ws.send(json.dumps({
            "id": 1, "cmd": "subscribe",
            "params": {"channels": ["orderbook_delta", "trade"], "market_tickers": tickers},
        }))

        while True:
            if duration_sec and time.monotonic() - start >= duration_sec:
                return
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
            except asyncio.TimeoutError:
                append_event(fp, {"kind": "coverage", "retrieved_at": now_iso(), "transport": "ws"})
                continue
            recv_at = now_iso()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                append_event(fp, {"kind": "coverage", "retrieved_at": recv_at, "transport": "ws"})
                append_event(fp, {
                    "kind": "capture_error", "stage": "ws_decode",
                    "start": recv_at, "end": recv_at, "error_type": "JSONDecodeError",
                })
                continue
            handle_message(books, msg, recv_at, fp, last_seq_by_sid)


async def main_async(args) -> int:
    tickers = sorted(set(args.ticker))
    if not tickers:
        raise RuntimeError("at least one --ticker is required")
    if args.reconnect_backoff_sec <= 0:
        raise RuntimeError("reconnect backoff must be positive")

    LOGS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = LOGS / f"ws-{stamp}.ndjson"
    run_started = time.monotonic()
    reconnect_gap_start: str | None = None
    attempts = 0

    with path.open("a", encoding="utf-8") as fp:
        append_event(fp, {
            "kind": "run_start", "started_at": now_iso(),
            "transport": "ws", "tickers": tickers,
            "economic_conclusion": "NO_PROVEN_EDGE",
            "live_trading": False, "paid_action": False, "wallet_action": False,
        })
        try:
            while True:
                if args.duration_sec:
                    elapsed = time.monotonic() - run_started
                    remaining = args.duration_sec - elapsed
                    if remaining <= 0:
                        break
                else:
                    remaining = 0

                state = {"connected": False}
                try:
                    await run_once(
                        tickers, fp, remaining,
                        reconnect_gap_start=reconnect_gap_start,
                        connection_state=state,
                    )
                    reconnect_gap_start = None
                    attempts = 0
                    if args.duration_sec:
                        break
                    # An unbounded session should only return if the socket ended
                    # cleanly; treat that as a reconnect boundary.
                    reconnect_gap_start = now_iso()
                except Exception as exc:
                    now = now_iso()
                    if state["connected"] or reconnect_gap_start is None:
                        reconnect_gap_start = now
                    append_event(fp, {
                        "kind": "capture_error", "stage": "ws_session",
                        "start": now, "end": now,
                        "error_type": type(exc).__name__,
                        "error": str(exc)[:300],
                        "credential_material_logged": False,
                    })

                if args.duration_sec and time.monotonic() - run_started >= args.duration_sec:
                    break
                attempts += 1
                delay = min(args.reconnect_backoff_sec * (2 ** min(attempts - 1, 4)), args.reconnect_backoff_max_sec)
                await asyncio.sleep(delay)
        finally:
            if reconnect_gap_start is not None:
                append_event(fp, {
                    "kind": "capture_gap", "start": reconnect_gap_start,
                    "end": now_iso(), "reason": "ws_reconnect_until_run_end",
                    "transport": "ws",
                })
            append_event(fp, {"kind": "run_end", "ended_at": now_iso(), "transport": "ws"})

    print(json.dumps({"status": "completed", "log": str(path), "economic_conclusion": "NO_PROVEN_EDGE"}, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", action="append", required=True)
    ap.add_argument("--duration-sec", type=float, default=0, help="0 = run until interrupted/disconnect")
    ap.add_argument("--reconnect-backoff-sec", type=float, default=1.0)
    ap.add_argument("--reconnect-backoff-max-sec", type=float, default=15.0)
    args = ap.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
