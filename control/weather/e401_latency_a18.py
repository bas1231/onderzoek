#!/usr/bin/env python3
"""A18: characterize KWI -> KXTEMP reaction latency from immutable E401 captures.

This is a research-only timing analyzer. It does not infer profitability and never
places orders. One primary sample remains city x KWI target minute; bucket-level
latencies are diagnostics nested under that event and are never counted as
independent primary evidence.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Iterable

import e401_sync_linker as sync
from market_reaction import (
    REACTION_OBSERVED,
    NO_REACTION_OBSERVED_WITHIN_WINDOW,
    UNPROVEN_REACTION,
    analyze_reaction,
)

STATE = Path.home() / ".local" / "state" / "prediction-research"
REPORTS = STATE / "e401_reaction_reports"


def percentile(values: Iterable[int], q: float) -> int | None:
    xs = sorted(int(x) for x in values)
    if not xs:
        return None
    if not 0 <= q <= 1:
        raise ValueError("q must be in [0,1]")
    # Nearest-rank style with linear index rounding, deterministic for small n.
    idx = int(round((len(xs) - 1) * q))
    return xs[idx]


def latency_bins(values: Iterable[int]) -> dict[str, int]:
    out = {"le_1s": 0, "gt_1s_le_3s": 0, "gt_3s_le_10s": 0, "gt_10s_le_30s": 0, "gt_30s": 0}
    for raw in values:
        x = int(raw)
        if x <= 1_000:
            out["le_1s"] += 1
        elif x <= 3_000:
            out["gt_1s_le_3s"] += 1
        elif x <= 10_000:
            out["gt_3s_le_10s"] += 1
        elif x <= 30_000:
            out["gt_10s_le_30s"] += 1
        else:
            out["gt_30s"] += 1
    return out


def stats(values: Iterable[int]) -> dict:
    xs = sorted(int(x) for x in values)
    if not xs:
        return {"n": 0, "min_ms": None, "median_ms": None, "p90_ms": None, "max_ms": None, "bins": latency_bins([])}
    return {
        "n": len(xs),
        "min_ms": xs[0],
        "median_ms": percentile(xs, 0.5),
        "p90_ms": percentile(xs, 0.9),
        "max_ms": xs[-1],
        "bins": latency_bins(xs),
    }


def analyze(window_ms: int = 30_000) -> dict:
    base = sync.build_report(window_ms)
    cycles = sync.load_completed_cycles()
    events = []
    event_latencies: list[int] = []
    bucket_latencies: list[int] = []
    reaction_kinds: Counter[str] = Counter()
    bucket_statuses: Counter[str] = Counter()

    for row in base.get("results") or []:
        if row.get("status") == UNPROVEN_REACTION:
            continue
        kwi_event = row.get("kwi_event") or {}
        city = str(kwi_event.get("city", "")).lower()
        event_ticker = row.get("event_ticker")
        bucket_tickers = list(row.get("bucket_tickers") or [])
        t0 = int(kwi_event.get("available_at_ms"))
        logs = sync.relevant_logs(cycles, city, event_ticker)
        bucket_rows = []

        for ticker in bucket_tickers:
            states, trades, gaps, coverage = sync.merge_capture(logs, ticker)
            gaps = list(gaps) + sync.synthetic_transport_gaps(coverage, t0 - 5_000, t0 + window_ms)
            r = analyze_reaction(
                kwi_event,
                states,
                trades,
                gaps,
                coverage,
                window_ms=window_ms,
                max_pre_age_ms=5_000,
                max_state_gap_ms=5_000,
            )
            status = r.get("status", "UNKNOWN")
            bucket_statuses[status] += 1
            entry = {"ticker": ticker, "status": status}
            if status == REACTION_OBSERVED:
                latency = int(r["latency_ms"])
                kind = str(r.get("reaction_kind") or "unknown")
                entry.update({"latency_ms": latency, "reaction_kind": kind})
                bucket_latencies.append(latency)
                reaction_kinds[kind] += 1
            elif status == UNPROVEN_REACTION:
                entry["reasons"] = r.get("reasons") or []
            elif status == NO_REACTION_OBSERVED_WITHIN_WINDOW:
                entry["latency_lower_bound_ms"] = int(r.get("latency_lower_bound_ms", window_ms))
            bucket_rows.append(entry)

        reacted = [b for b in bucket_rows if b.get("status") == REACTION_OBSERVED]
        if reacted:
            event_latency = min(int(b["latency_ms"]) for b in reacted)
            event_latencies.append(event_latency)
            first = sorted(b["ticker"] for b in reacted if int(b["latency_ms"]) == event_latency)
        else:
            event_latency = None
            first = []

        events.append({
            "city": city,
            "kwi_t": kwi_event.get("kwi_t"),
            "available_at_ms": t0,
            "event_ticker": event_ticker,
            "event_target_at_ms": row.get("event_target_at_ms"),
            "horizon_to_settlement_ms": row.get("horizon_to_settlement_ms"),
            "event_status": row.get("status"),
            "first_reaction_latency_ms": event_latency,
            "first_reaction_tickers": first,
            "bucket_results": bucket_rows,
        })

    city_counts = Counter(e["city"] for e in events)
    report = {
        "schema": "KAL_WX_MARKET_REACTION_LATENCY_A18_V1",
        "task": "EDGE-HUNTER-KWI-REACTION-LATENCY-E401A18",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_ms": window_ms,
        "primary_event_semantics": "one event per city x first-decision-eligible KWI target minute; bucket diagnostics are not independent samples",
        "base_primary_events_total": base.get("primary_events_total", 0),
        "base_evaluable_primary_events": base.get("evaluable_primary_events", 0),
        "analyzed_primary_events": len(events),
        "cities": dict(sorted(city_counts.items())),
        "event_first_reaction_latency": stats(event_latencies),
        "bucket_reaction_latency": stats(bucket_latencies),
        "bucket_status_counts": dict(sorted(bucket_statuses.items())),
        "reaction_kind_counts": dict(sorted(reaction_kinds.items())),
        "events": events,
        "interpretation_guard": [
            "Observed reaction latency is market activity after first KWI availability, not evidence of economic edge.",
            "Latency measured from local first-seen KWI manifest retrieval to locally received Kalshi WS state/trade evidence.",
            "Clock/network-path differences remain part of measured end-to-end latency and must not be silently normalized away.",
            "Execution-realistic edge requires later bid/ask, fees, slippage, fill probability and out-of-sample validation.",
        ],
        "economic_conclusion": "NO_PROVEN_EDGE",
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
    }
    return report


def main() -> int:
    report = analyze()
    REPORTS.mkdir(parents=True, exist_ok=True)
    path = REPORTS / "e401-a18-latency-latest.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    compact = {
        "task": report["task"],
        "status": "PASS",
        "report": str(path),
        "analyzed_primary_events": report["analyzed_primary_events"],
        "cities": report["cities"],
        "event_first_reaction_latency": report["event_first_reaction_latency"],
        "bucket_reaction_latency": report["bucket_reaction_latency"],
        "reaction_kind_counts": report["reaction_kind_counts"],
        "bucket_status_counts": report["bucket_status_counts"],
        "economic_conclusion": report["economic_conclusion"],
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
    }
    print(json.dumps(compact, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
