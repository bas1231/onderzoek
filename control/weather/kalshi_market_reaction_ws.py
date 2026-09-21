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


async def run_once(tickers: list[str], fp, duration_sec: float) -> None:
    try:
        import websockets
    except ImportError as exc:
        raise RuntimeError("websockets package required") from exc

    key_id, private_key = load_auth()
    headers = auth_headers(key_id, private_key)
    books = {t: OrderBook(t) for t in tickers}
    start = time.monotonic()

    # websockets >= 14 uses additional_headers; older releases use extra_headers.
    params = inspect.signature(websockets.connect).parameters
    header_kw = "additional_headers" if "additional_headers" in params else "extra_headers"
    ws_cm = websockets.connect(WS_URL, **{header_kw: headers})

    async with ws_cm as ws:
        append_event(fp, {
            "kind": "ws_connected", "retrieved_at": now_iso(),
            "tickers": tickers, "credential_material_logged": False,
        })
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
                append_event(fp, {
                    "kind": "capture_error", "stage": "ws_decode",
                    "start": recv_at, "end": recv_at, "error_type": "JSONDecodeError",
                })
                continue

            # Raw market-data frame, timestamped on receipt.
            append_event(fp, {
                "kind": "ws_raw", "retrieved_at": recv_at,
                "type": msg.get("type"), "sid": msg.get("sid"), "seq": msg.get("seq"),
                "msg": msg.get("msg"),
            })

            typ = msg.get("type")
            if typ == "orderbook_snapshot":
                ticker = (msg.get("msg") or {}).get("market_ticker")
                if ticker in books:
                    try:
                        s = books[ticker].snapshot(msg, recv_at)
                        append_event(fp, {"kind": "market_state", "retrieved_at": recv_at, **s.as_json()})
                    except Exception as exc:
                        append_event(fp, {
                            "kind": "capture_gap", "ticker": ticker,
                            "start": recv_at, "end": recv_at,
                            "reason": f"snapshot_reconstruction:{type(exc).__name__}:{str(exc)[:200]}",
                        })
            elif typ == "orderbook_delta":
                ticker = (msg.get("msg") or {}).get("market_ticker")
                if ticker in books:
                    try:
                        s = books[ticker].delta(msg, recv_at)
                        append_event(fp, {"kind": "market_state", "retrieved_at": recv_at, **s.as_json()})
                    except Exception as exc:
                        append_event(fp, {
                            "kind": "capture_gap", "ticker": ticker,
                            "start": recv_at, "end": recv_at,
                            "reason": f"delta_reconstruction:{type(exc).__name__}:{str(exc)[:200]}",
                        })
                        # Never continue trusting a book after a broken sequence.
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


async def main_async(args) -> int:
    tickers = sorted(set(args.ticker))
    if not tickers:
        raise RuntimeError("at least one --ticker is required")
    LOGS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = LOGS / f"ws-{stamp}.ndjson"

    with path.open("a", encoding="utf-8") as fp:
        append_event(fp, {
            "kind": "run_start", "started_at": now_iso(),
            "transport": "ws", "tickers": tickers,
            "economic_conclusion": "NO_PROVEN_EDGE",
            "live_trading": False, "paid_action": False, "wallet_action": False,
        })
        try:
            await run_once(tickers, fp, args.duration_sec)
        except Exception as exc:
            now = now_iso()
            append_event(fp, {
                "kind": "capture_gap", "start": now, "end": now,
                "reason": f"ws_session:{type(exc).__name__}",
            })
            raise
        finally:
            append_event(fp, {"kind": "run_end", "ended_at": now_iso(), "transport": "ws"})
    print(json.dumps({"status": "completed", "log": str(path), "economic_conclusion": "NO_PROVEN_EDGE"}, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", action="append", required=True)
    ap.add_argument("--duration-sec", type=float, default=0, help="0 = run until interrupted/disconnect")
    args = ap.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
