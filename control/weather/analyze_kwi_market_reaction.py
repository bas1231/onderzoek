#!/usr/bin/env python3
"""Offline KWI -> market reaction analyzer for E401."""
from __future__ import annotations

import argparse
from decimal import Decimal
import json
from pathlib import Path

from market_reaction import MarketState, analyze_reaction, extract_kwi_events, market_state_from_rest, parse_ts_ms


def load_jsons(path: Path):
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(path.glob("kwi-*.json"))]


def load_capture(path: Path, ticker: str):
    states, trades, gaps, coverage = [], [], [], []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                gaps.append({"start": 0, "end": 9_999_999_999_999, "reason": f"malformed_line_{line_no}"})
                continue
            if e.get("ticker") not in (None, ticker):
                continue
            kind = e.get("kind")
            if kind == "orderbook_rest" and e.get("ticker") == ticker:
                try:
                    states.append(market_state_from_rest(ticker, e["retrieved_at"], e["payload"]))
                except Exception:
                    gaps.append({"start": e.get("request_started_at", e.get("retrieved_at")), "end": e.get("retrieved_at"), "reason": "rest_parse"})
            elif kind == "market_state" and e.get("ticker") == ticker:
                try:
                    states.append(MarketState(
                        ticker=ticker,
                        ts_ms=int(e["ts_ms"]),
                        yes_bid=None if e.get("yes_bid") is None else Decimal(e["yes_bid"]),
                        yes_ask=None if e.get("yes_ask") is None else Decimal(e["yes_ask"]),
                        no_bid=None if e.get("no_bid") is None else Decimal(e["no_bid"]),
                        no_ask=None if e.get("no_ask") is None else Decimal(e["no_ask"]),
                        yes_bid_qty=None if e.get("yes_bid_qty") is None else Decimal(e["yes_bid_qty"]),
                        no_bid_qty=None if e.get("no_bid_qty") is None else Decimal(e["no_bid_qty"]),
                        transport=e.get("transport", "ws"),
                        seq=e.get("seq"),
                    ))
                except Exception:
                    gaps.append({"start": e.get("retrieved_at", 0), "end": e.get("retrieved_at", 9_999_999_999_999), "reason": "state_parse"})
            elif kind == "trades_rest":
                trades.extend(e.get("trades") or [])
            elif kind == "trade":
                trades.append(e)
            elif kind == "coverage":
                try:
                    coverage.append(parse_ts_ms(e.get("retrieved_at")))
                except ValueError:
                    gaps.append({"start": 0, "end": 9_999_999_999_999, "reason": "coverage_parse"})
            elif kind in ("capture_gap", "capture_error"):
                gaps.append({"start": e.get("start", e.get("retrieved_at", 0)), "end": e.get("end", e.get("retrieved_at", 9_999_999_999_999)), "reason": e.get("reason", kind)})
    return states, trades, gaps, coverage


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kwi-manifest-dir", type=Path, required=True)
    ap.add_argument("--market-log", type=Path, required=True)
    ap.add_argument("--city", required=True)
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--window-ms", type=int, default=30_000)
    ap.add_argument("--max-pre-age-ms", type=int, default=5_000)
    ap.add_argument("--max-state-gap-ms", type=int, default=5_000)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    manifests = load_jsons(args.kwi_manifest_dir)
    kwi_events = extract_kwi_events(manifests, args.city)
    states, trades, gaps, coverage = load_capture(args.market_log, args.ticker)
    results = [
        analyze_reaction(
            event, states, trades, gaps, coverage,
            window_ms=args.window_ms,
            max_pre_age_ms=args.max_pre_age_ms,
            max_state_gap_ms=args.max_state_gap_ms,
        )
        for event in kwi_events
    ]
    report = {
        "schema": "KAL_WX_MARKET_REACTION_E401_V1",
        "candidate": "KAL-WX-INDEX-001",
        "city": args.city,
        "ticker": args.ticker,
        "window_ms": args.window_ms,
        "events_total": len(results),
        "results": results,
        "economic_conclusion": "NO_PROVEN_EDGE",
        "guards": [
            "Reaction latency is not profitability.",
            "KWI public availability does not by itself prove settlement equivalence.",
            "Capture gaps and inadequate pre/post coverage fail closed.",
            "No hindsight data may be used as point-in-time evidence.",
        ],
    }
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
