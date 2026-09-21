#!/usr/bin/env python3
"""Read-only Kalshi market capture for KWI reaction research.

Uses only GET market-data endpoints. No order, portfolio, wallet, or write
endpoint is present. Every response/error is timestamped and append-only.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from urllib.parse import urlencode, quote
import urllib.request

BASE = "https://external-api.kalshi.com/trade-api/v2"
UA = "PredictionResearch-KWI-market-reaction-readonly/1"
HOME = Path.home()
STATE = HOME / ".local" / "state" / "prediction-research"
RAW = STATE / "raw" / "kalshi_market_reaction"
LOGS = STATE / "kalshi_market_reaction_logs"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch_json(url: str, timeout: float = 10.0) -> tuple[int, bytes, dict]:
    req = urllib.request.Request(url, headers={"User-Agent": UA}, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read(10_000_000)
        status = int(getattr(r, "status", 200))
    return status, body, json.loads(body.decode("utf-8"))


def persist_raw(kind: str, ticker: str, body: bytes) -> tuple[str, str]:
    sha = hashlib.sha256(body).hexdigest()
    d = RAW / kind / ticker
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{sha}.json"
    if not path.exists():
        path.write_bytes(body)
    return sha, str(path)


def append_event(fp, event: dict) -> None:
    fp.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
    fp.flush()


def discover(series_ticker: str) -> list[str]:
    q = urlencode({"series_ticker": series_ticker, "status": "open", "limit": 1000})
    _, _, data = fetch_json(f"{BASE}/markets?{q}")
    return sorted({m.get("ticker") for m in data.get("markets", []) if m.get("ticker")})


def capture_orderbook(fp, ticker: str, timeout: float) -> bool:
    start = now_iso()
    url = f"{BASE}/markets/{quote(ticker, safe='')}/orderbook"
    try:
        status, body, payload = fetch_json(url, timeout)
        retrieved = now_iso()
        sha, raw_path = persist_raw("orderbook", ticker, body)
        append_event(fp, {
            "kind": "orderbook_rest", "ticker": ticker,
            "request_started_at": start, "retrieved_at": retrieved,
            "http_status": status, "sha256": sha, "raw_path": raw_path,
            "payload": payload, "transport": "rest",
            "live_trading": False, "paid_action": False, "wallet_action": False,
        })
        return True
    except Exception as exc:
        append_event(fp, {
            "kind": "capture_error", "ticker": ticker,
            "start": start, "end": now_iso(), "stage": "orderbook_rest",
            "error_type": type(exc).__name__, "error": str(exc)[:500],
            "transport": "rest",
        })
        return False


def capture_trades(fp, ticker: str, timeout: float, seen: set[str]) -> bool:
    start = now_iso()
    q = urlencode({"ticker": ticker, "limit": 100, "is_block_trade": "false"})
    url = f"{BASE}/markets/trades?{q}"
    try:
        status, body, payload = fetch_json(url, timeout)
        retrieved = now_iso()
        sha, raw_path = persist_raw("trades", ticker, body)
        new = []
        for trade in payload.get("trades", []):
            tid = trade.get("trade_id")
            if tid and tid not in seen:
                seen.add(tid)
                new.append(trade)
        append_event(fp, {
            "kind": "trades_rest", "ticker": ticker,
            "request_started_at": start, "retrieved_at": retrieved,
            "http_status": status, "sha256": sha, "raw_path": raw_path,
            "trades": new, "transport": "rest",
        })
        return True
    except Exception as exc:
        append_event(fp, {
            "kind": "capture_error", "ticker": ticker,
            "start": start, "end": now_iso(), "stage": "trades_rest",
            "error_type": type(exc).__name__, "error": str(exc)[:500],
            "transport": "rest",
        })
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", action="append", default=[], help="Market ticker; repeatable")
    ap.add_argument("--series-ticker", help="Discover all currently open markets in this series")
    ap.add_argument("--poll-ms", type=int, default=1000)
    ap.add_argument("--duration-sec", type=float, default=0, help="0 = run until interrupted")
    ap.add_argument("--timeout-sec", type=float, default=10)
    ap.add_argument("--no-trades", action="store_true")
    args = ap.parse_args()

    if args.poll_ms < 250:
        raise SystemExit("poll-ms below 250 is intentionally blocked; use WebSocket for finer capture")
    tickers = set(args.ticker)
    if args.series_ticker:
        tickers.update(discover(args.series_ticker))
    tickers = sorted(tickers)
    if not tickers:
        raise SystemExit("no market tickers resolved")

    LOGS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = LOGS / f"rest-{stamp}.ndjson"
    started_mono = time.monotonic()
    seen: dict[str, set[str]] = {t: set() for t in tickers}

    with log_path.open("a", encoding="utf-8") as fp:
        append_event(fp, {
            "kind": "run_start", "started_at": now_iso(), "transport": "rest",
            "tickers": tickers, "poll_ms": args.poll_ms,
            "economic_conclusion": "NO_PROVEN_EDGE",
            "live_trading": False, "paid_action": False, "wallet_action": False,
        })
        try:
            while True:
                cycle_start = time.monotonic()
                for ticker in tickers:
                    capture_orderbook(fp, ticker, args.timeout_sec)
                    if not args.no_trades:
                        capture_trades(fp, ticker, args.timeout_sec, seen[ticker])
                if args.duration_sec and time.monotonic() - started_mono >= args.duration_sec:
                    break
                elapsed = time.monotonic() - cycle_start
                time.sleep(max(0, args.poll_ms / 1000 - elapsed))
        except KeyboardInterrupt:
            pass
        finally:
            append_event(fp, {"kind": "run_end", "ended_at": now_iso(), "transport": "rest"})

    print(json.dumps({
        "status": "completed", "log": str(log_path), "tickers": tickers,
        "economic_conclusion": "NO_PROVEN_EDGE",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
