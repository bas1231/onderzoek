#!/usr/bin/env python3
"""Offline CLI for KAL-WX-MARKET-REACTION-E401.

Reads already-captured KWI manifests and already-captured market-state/trade JSONL.
No network, credentials, orders, or paid services are used.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from control.weather.kwi_market_reaction_e401 import MarketState, analyze_reaction, extract_kwi_events


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path):
    rows=[]
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line=line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def state_from_row(row):
    return MarketState(
        ticker=row["ticker"], ts_ms=int(row["ts_ms"]),
        yes_bid=row.get("yes_bid"), yes_ask=row.get("yes_ask"),
        no_bid=row.get("no_bid"), no_ask=row.get("no_ask"),
        yes_bid_qty=row.get("yes_bid_qty"), no_bid_qty=row.get("no_bid_qty"),
        transport=row.get("transport", "unknown"), seq=row.get("seq"),
    )


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--city", required=True)
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--manifests", type=Path, nargs="+", required=True)
    ap.add_argument("--states", type=Path, required=True)
    ap.add_argument("--trades", type=Path)
    ap.add_argument("--gaps", type=Path)
    ap.add_argument("--coverage", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--window-ms", type=int, default=30000)
    args=ap.parse_args()

    manifests=[load_json(p) for p in args.manifests]
    events=[e for e in extract_kwi_events(manifests,args.city) if e["kind"]=="first_decision_eligible"]
    states=[state_from_row(r) for r in load_jsonl(args.states) if r.get("ticker")==args.ticker]
    trades=load_jsonl(args.trades) if args.trades else []
    gaps=load_jsonl(args.gaps) if args.gaps else []
    coverage=[]
    if args.coverage:
        coverage=[int(r["ts_ms"]) for r in load_jsonl(args.coverage) if "ts_ms" in r]

    results=[analyze_reaction(e,states,trades=trades,gaps=gaps,coverage_ms=coverage,window_ms=args.window_ms) for e in events]
    payload={
        "experiment_id":"KAL-WX-MARKET-REACTION-E401",
        "city":args.city,
        "ticker":args.ticker,
        "event_count":len(events),
        "results":results,
        "economic_status":"NO_PROVEN_EDGE",
    }
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2,sort_keys=True))


if __name__=="__main__":
    main()
