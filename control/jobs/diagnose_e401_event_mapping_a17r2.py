#!/usr/bin/env python3
"""Diagnose E401 KWI-target to hourly-event mapping without changing evidence rules."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path.cwd()
WEATHER = ROOT / "control" / "weather"
sys.path.insert(0, str(WEATHER))

from market_reaction import extract_kwi_events  # noqa: E402
from e401_sync_linker import (  # noqa: E402
    event_local_hour,
    event_matches_target,
    load_completed_cycles,
    load_kwi_manifests,
    target_local_hour,
)

TASK = "EDGE-HUNTER-KWI-EVENT-MAPPING-DIAG-E401A17R2"

cycles = load_completed_cycles()
manifests = load_kwi_manifests()

report = {
    "task": TASK,
    "status": "PASS",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "completed_cycle_count": len(cycles),
    "prospective_start_ms": min((c["started_ms"] for c in cycles), default=None),
    "events": [],
    "summary": {},
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "economic_conclusion": "NO_PROVEN_EDGE",
}

if not cycles:
    report["status"] = "COLLECTING_NO_COMPLETED_CAPTURE"
    print(json.dumps(report, indent=2, sort_keys=True))
    raise SystemExit(0)

prospective_start = min(c["started_ms"] for c in cycles)
summary = defaultdict(lambda: {
    "primary_events": 0,
    "with_any_pre_signal_discovery": 0,
    "with_parseable_pre_signal_event": 0,
    "with_exact_hour_match": 0,
})

for city in ("nyc", "miami", "chicago"):
    for event in extract_kwi_events(manifests, city):
        if event.get("kind") != "first_decision_eligible":
            continue
        t0 = int(event.get("available_at_ms", 0))
        if t0 < prospective_start:
            continue
        target_hour = target_local_hour(city, event.get("kwi_t"))
        pre = []
        for cycle in cycles:
            if cycle["discovery_ms"] > t0:
                continue
            for row in cycle["discovery"].get("series") or []:
                if str(row.get("city", "")).lower() != city:
                    continue
                for discovered in row.get("events") or []:
                    ticker = discovered.get("event_ticker")
                    if not ticker:
                        continue
                    parsed = event_local_hour(ticker)
                    pre.append({
                        "discovery_ms": cycle["discovery_ms"],
                        "event_ticker": ticker,
                        "parsed_event_local_hour": parsed,
                        "market_count": discovered.get("market_count"),
                        "exact_hour_match": event_matches_target(city, ticker, event.get("kwi_t")),
                    })
        pre.sort(key=lambda x: (x["discovery_ms"], x["event_ticker"]))
        unique = []
        seen = set()
        for row in pre:
            key = (row["event_ticker"], row["discovery_ms"])
            if key in seen:
                continue
            seen.add(key)
            unique.append(row)
        exact = [x for x in unique if x["exact_hour_match"]]
        parseable = [x for x in unique if x["parsed_event_local_hour"] is not None]

        summary[city]["primary_events"] += 1
        if unique:
            summary[city]["with_any_pre_signal_discovery"] += 1
        if parseable:
            summary[city]["with_parseable_pre_signal_event"] += 1
        if exact:
            summary[city]["with_exact_hour_match"] += 1

        if len(report["events"]) < 40:
            report["events"].append({
                "city": city,
                "available_at_ms": t0,
                "kwi_t": event.get("kwi_t"),
                "target_local_hour": target_hour,
                "pre_signal_discovery_count": len(unique),
                "exact_match_count": len(exact),
                "latest_pre_signal_discoveries": unique[-6:],
            })

report["summary"] = {city: vals for city, vals in sorted(summary.items())}
print(json.dumps(report, indent=2, sort_keys=True))
