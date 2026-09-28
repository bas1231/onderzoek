#!/usr/bin/env python3
"""Build one fail-closed E401 reaction sample per city x KWI target minute.

The linker uses only archived point-in-time artifacts. Bucket markets belonging to
one hourly event are evaluated together and never count as independent samples.
Revisions are retained as diagnostics and never inflate the primary sample.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control" / "weather"))

from market_reaction import (  # noqa: E402
    ECONOMIC_CONCLUSION,
    NO_REACTION_OBSERVED_WITHIN_WINDOW,
    REACTION_OBSERVED,
    UNPROVEN_REACTION,
    analyze_reaction,
    extract_kwi_events,
    parse_ts_ms,
)
from analyze_kwi_market_reaction import load_capture  # noqa: E402

STATE = Path.home() / ".local" / "state" / "prediction-research"
PROSPECTIVE = STATE / "e401_prospective_manifests"
KWI_MANIFESTS = STATE / "kalshi_weather_index_manifests"
REPORTS = STATE / "e401_reaction_reports"

CITY_TZ = {
    "nyc": "America/New_York",
    "miami": "America/New_York",
    "chicago": "America/Chicago",
}
MONTHS = {m: i for i, m in enumerate(
    ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"), 1
)}
EVENT_RE = re.compile(r"-(\d{2})([A-Z]{3})(\d{2})(\d{2})$")


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def event_local_hour(event_ticker: str):
    match = EVENT_RE.search(str(event_ticker or ""))
    if not match:
        return None
    yy, mon, day, hour = match.groups()
    month = MONTHS.get(mon)
    if month is None:
        return None
    try:
        return 2000 + int(yy), month, int(day), int(hour)
    except ValueError:
        return None


def target_local_hour(city: str, kwi_t) -> tuple[int, int, int, int] | None:
    tz_name = CITY_TZ.get(city)
    if tz_name is None:
        return None
    try:
        dt = datetime.fromtimestamp(parse_ts_ms(kwi_t) / 1000, tz=timezone.utc).astimezone(ZoneInfo(tz_name))
    except Exception:
        return None
    return dt.year, dt.month, dt.day, dt.hour


def event_matches_target(city: str, event_ticker: str, kwi_t) -> bool:
    return event_local_hour(event_ticker) == target_local_hour(city, kwi_t)


def event_target_ms(event_ticker: str) -> int | None:
    """Return the exact KXTEMP market target time encoded in the ticker.

    Kalshi hourly temperature market titles use Eastern Time (EDT/EST); the
    ticker's terminal hour is that exact market target hour.
    """
    parsed = event_local_hour(event_ticker)
    if parsed is None:
        return None
    year, month, day, hour = parsed
    try:
        dt = datetime(year, month, day, hour, 0, 0, tzinfo=ZoneInfo("America/New_York"))
    except Exception:
        return None
    return int(dt.timestamp() * 1000)


def load_kwi_manifests() -> list[dict]:
    out = []
    for path in sorted(KWI_MANIFESTS.glob("kwi-*.json")) if KWI_MANIFESTS.is_dir() else []:
        obj = read_json(path)
        if isinstance(obj, dict):
            out.append(obj)
    return out


def load_completed_cycles() -> list[dict]:
    cycles = []
    for path in sorted(PROSPECTIVE.glob("cycle-*.json")) if PROSPECTIVE.is_dir() else []:
        obj = read_json(path)
        if not isinstance(obj, dict):
            continue
        capture = obj.get("capture")
        summary = capture.get("summary") if isinstance(capture, dict) else None
        log_value = summary.get("log") if isinstance(summary, dict) else None
        if not log_value:
            continue
        discovery_path = obj.get("discovery_manifest")
        discovery = read_json(Path(discovery_path)) if discovery_path else None
        if not isinstance(discovery, dict):
            continue
        try:
            started_ms = parse_ts_ms(obj.get("started_at"))
            finished_ms = parse_ts_ms(obj.get("finished_at"))
            discovery_ms = parse_ts_ms(discovery.get("retrieved_at"))
        except Exception:
            continue
        cycles.append({
            "started_ms": started_ms,
            "finished_ms": finished_ms,
            "discovery_ms": discovery_ms,
            "log": Path(log_value),
            "discovery": discovery,
        })
    return sorted(cycles, key=lambda x: x["started_ms"])


def matching_event_snapshot(cycles: list[dict], city: str, kwi_event: dict):
    """Nearest future hourly event known before signal availability.

    A Weather Index point is a minute-resolution observation, not the hourly
    contract's settlement timestamp. For reaction analysis, select the nearest
    hourly target still in the future at signal availability, using only event
    discovery snapshots that already existed before that signal. For one ticker,
    the latest pre-signal discovery snapshot wins.
    """
    t0 = int(kwi_event["available_at_ms"])
    by_ticker = {}
    for cycle in cycles:
        discovery_ms = int(cycle["discovery_ms"])
        if discovery_ms > t0:
            continue
        for row in cycle["discovery"].get("series") or []:
            if str(row.get("city", "")).lower() != city:
                continue
            for event in row.get("events") or []:
                ticker = event.get("event_ticker")
                target_ms = event_target_ms(ticker) if ticker else None
                tickers = sorted(set(event.get("market_tickers") or []))
                if target_ms is None or target_ms <= t0 or not tickers:
                    continue
                prev = by_ticker.get(ticker)
                if prev is None or discovery_ms > prev[0]:
                    by_ticker[ticker] = (discovery_ms, target_ms, event, tickers)
    if not by_ticker:
        return None
    ticker, (discovery_ms, target_ms, event, tickers) = min(
        by_ticker.items(),
        key=lambda item: (item[1][1], -item[1][0], item[0]),
    )
    return {
        "event_ticker": ticker,
        "market_tickers": tickers,
        "event_target_at_ms": target_ms,
        "event_discovered_at_ms": discovery_ms,
        "horizon_to_settlement_ms": target_ms - t0,
    }

def relevant_logs(cycles: list[dict], city: str, event_ticker: str) -> list[Path]:
    logs = []
    for cycle in cycles:
        found = False
        for row in cycle["discovery"].get("series") or []:
            if str(row.get("city", "")).lower() != city:
                continue
            if any(e.get("event_ticker") == event_ticker for e in row.get("events") or []):
                found = True
                break
        if found and cycle["log"].is_file():
            logs.append(cycle["log"])
    return sorted(set(logs))


def merge_capture(logs: list[Path], ticker: str):
    states, trades, gaps, coverage = [], [], [], []
    for path in logs:
        s, t, g, c = load_capture(path, ticker)
        states.extend(s)
        trades.extend(t)
        gaps.extend(g)
        coverage.extend(c)
    state_seen = set()
    dedup_states = []
    for state in sorted(states, key=lambda x: (x.ts_ms, -1 if x.seq is None else x.seq)):
        key = (state.ts_ms, state.seq, state.fingerprint)
        if key not in state_seen:
            state_seen.add(key)
            dedup_states.append(state)
    coverage = sorted(set(int(x) for x in coverage))
    return dedup_states, trades, gaps, coverage


def synthetic_transport_gaps(coverage: list[int], start_ms: int, end_ms: int, max_gap_ms: int = 2500):
    points = sorted(set(x for x in coverage if start_ms <= x <= end_ms))
    out = []
    for a, b in zip(points, points[1:]):
        if b - a > max_gap_ms:
            out.append({
                "start": a,
                "end": b,
                "reason": f"cross_log_transport_gap_gt_{max_gap_ms}ms",
            })
    return out


def composite_result(kwi_event: dict, event_snapshot: dict | None, cycles: list[dict], *, window_ms: int):
    city = str(kwi_event.get("city", "")).lower()
    t0 = int(kwi_event["available_at_ms"])
    if event_snapshot is None:
        return {
            "status": UNPROVEN_REACTION,
            "economic_conclusion": ECONOMIC_CONCLUSION,
            "reasons": ["NO_PRE_SIGNAL_FUTURE_HOURLY_EVENT_DISCOVERY"],
            "kwi_event": kwi_event,
            "bucket_count": 0,
        }

    event_ticker = event_snapshot["event_ticker"]
    tickers = event_snapshot["market_tickers"]
    logs = relevant_logs(cycles, city, event_ticker)
    bucket_results = {}
    for ticker in tickers:
        states, trades, gaps, coverage = merge_capture(logs, ticker)
        gaps = list(gaps) + synthetic_transport_gaps(coverage, t0 - 5000, t0 + window_ms)
        bucket_results[ticker] = analyze_reaction(
            kwi_event,
            states,
            trades,
            gaps,
            coverage,
            window_ms=window_ms,
            max_pre_age_ms=5000,
            max_state_gap_ms=5000,
        )

    unproven = {t: r for t, r in bucket_results.items() if r.get("status") == UNPROVEN_REACTION}
    reacted = {t: r for t, r in bucket_results.items() if r.get("status") == REACTION_OBSERVED}
    base = {
        "economic_conclusion": ECONOMIC_CONCLUSION,
        "kwi_event": kwi_event,
        "event_ticker": event_ticker,
        "event_target_at_ms": event_snapshot.get("event_target_at_ms"),
        "event_discovered_at_ms": event_snapshot.get("event_discovered_at_ms"),
        "horizon_to_settlement_ms": event_snapshot.get("horizon_to_settlement_ms"),
        "bucket_count": len(tickers),
        "bucket_tickers": tickers,
        "capture_log_count": len(logs),
        "bucket_status_counts": {
            REACTION_OBSERVED: len(reacted),
            NO_REACTION_OBSERVED_WITHIN_WINDOW: sum(
                1 for r in bucket_results.values() if r.get("status") == NO_REACTION_OBSERVED_WITHIN_WINDOW
            ),
            UNPROVEN_REACTION: len(unproven),
        },
    }
    if unproven:
        reasons = []
        for ticker, result in sorted(unproven.items()):
            for reason in result.get("reasons") or ["UNSPECIFIED"]:
                reasons.append(f"{ticker}:{reason}")
        return {**base, "status": UNPROVEN_REACTION, "reasons": reasons}
    if reacted:
        latency = min(int(r["latency_ms"]) for r in reacted.values())
        reaction_tickers = sorted(t for t, r in reacted.items() if int(r["latency_ms"]) == latency)
        return {
            **base,
            "status": REACTION_OBSERVED,
            "latency_ms": latency,
            "reaction_tickers": reaction_tickers,
        }
    return {
        **base,
        "status": NO_REACTION_OBSERVED_WITHIN_WINDOW,
        "latency_lower_bound_ms": window_ms,
    }


def build_report(window_ms: int = 30000) -> dict:
    cycles = load_completed_cycles()
    manifests = load_kwi_manifests()
    if not cycles:
        return {
            "schema": "KAL_WX_MARKET_REACTION_E401_V2",
            "task": "EDGE-HUNTER-KWI-SYNC-LINK-E401A17",
            "status": "COLLECTING_NO_COMPLETED_CAPTURE",
            "primary_events_total": 0,
            "results": [],
            "revision_events_total": 0,
            "economic_conclusion": ECONOMIC_CONCLUSION,
        }

    prospective_start_ms = min(c["started_ms"] for c in cycles)
    latest_complete_ms = max(c["finished_ms"] for c in cycles)
    primary_events = []
    revisions = []
    for city in CITY_TZ:
        for event in extract_kwi_events(manifests, city):
            if int(event.get("available_at_ms", 0)) < prospective_start_ms:
                continue
            if event.get("kind") == "first_decision_eligible":
                primary_events.append(event)
            elif event.get("kind") == "revision":
                revisions.append(event)

    primary_events.sort(key=lambda e: int(e["available_at_ms"]))
    finalized = []
    pending = []
    for event in primary_events:
        t0 = int(event["available_at_ms"])
        if latest_complete_ms < t0 + window_ms:
            pending.append(event)
            continue
        city = str(event["city"]).lower()
        snapshot = matching_event_snapshot(cycles, city, event)
        finalized.append(composite_result(event, snapshot, cycles, window_ms=window_ms))

    evaluable = [r for r in finalized if r.get("status") != UNPROVEN_REACTION]
    cities = sorted({str(r.get("kwi_event", {}).get("city", "")).lower() for r in evaluable if r.get("kwi_event")})
    coverage = len(evaluable) / len(finalized) if finalized else 0.0
    return {
        "schema": "KAL_WX_MARKET_REACTION_E401_V2",
        "task": "EDGE-HUNTER-KWI-SYNC-LINK-E401A17",
        "candidate": "KAL-WX-INDEX-001",
        "status": "COLLECTING",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "prospective_start_at_ms": prospective_start_ms,
        "latest_completed_capture_at_ms": latest_complete_ms,
        "window_ms": window_ms,
        "primary_events_total": len(finalized),
        "pending_primary_events_total": len(pending),
        "revision_events_total": len(revisions),
        "ignored_nonprimary_events_total": 0,
        "sample_count_semantics": "one primary sample per city x KWI target minute; all buckets of the matching hourly event are one composite reaction sample",
        "results": finalized,
        "revision_results": [],
        "evaluable_primary_events": len(evaluable),
        "evaluable_cities": cities,
        "valid_synchronized_capture_fraction": coverage,
        "economic_conclusion": ECONOMIC_CONCLUSION,
        "guards": [
            "Only first_decision_eligible KWI events after prospective capture start enter the primary sample.",
            "Same-target revisions never count as independent evidence.",
            "The linked hourly event must have been discovered at or before signal availability and its exact target time must still be in the future.",
            "Among eligible pre-signal discoveries, the nearest future hourly target is selected; KWI minute timestamps are never treated as settlement timestamps.",
            "All bucket tickers from the pre-signal event snapshot must be evaluable or the composite event is UNPROVEN_REACTION.",
            "A reaction is activity, not market edge or profitability.",
            "NO_PROVEN_EDGE remains until later executable-price testing succeeds out of sample.",
        ],
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--window-ms", type=int, default=30000)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    if args.window_ms <= 0:
        raise SystemExit("window must be positive")
    report = build_report(args.window_ms)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        REPORTS.mkdir(parents=True, exist_ok=True)
        path = REPORTS / "e401-a17-latest.json"
        path.write_text(text, encoding="utf-8")
        print(text, end="")
        print(json.dumps({"report": str(path), "economic_conclusion": ECONOMIC_CONCLUSION}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
