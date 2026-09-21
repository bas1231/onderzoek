#!/usr/bin/env python3
from datetime import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control" / "weather"))

import e401_sync_linker as m


def epoch_ms(iso: str) -> int:
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() * 1000)


def discovery(city, events):
    return {"series": [{"city": city, "events": events}]}


def evt(ticker, tickers):
    return {"event_ticker": ticker, "market_tickers": tickers}


def test_ticker_hour_is_exact_eastern_market_time():
    # Sep 21 is EDT: 13:00 ET == 17:00 UTC, including Chicago series.
    assert m.event_target_ms("KXTEMPMIAH-26SEP2113") == epoch_ms("2026-09-21T17:00:00Z")
    assert m.event_target_ms("KXTEMPNYCH-26SEP2113") == epoch_ms("2026-09-21T17:00:00Z")
    assert m.event_target_ms("KXTEMPCHIH-26SEP2113") == epoch_ms("2026-09-21T17:00:00Z")


def test_nearest_future_pre_signal_event_is_selected():
    signal_ms = epoch_ms("2026-09-21T16:08:19Z")
    event = {"city": "miami", "kwi_t": epoch_ms("2026-09-21T16:06:00Z"), "available_at_ms": signal_ms}
    cycles = [
        {"discovery_ms": signal_ms - 5000, "discovery": discovery("miami", [
            evt("KXTEMPMIAH-26SEP2113", ["A", "B"]),
            evt("KXTEMPMIAH-26SEP2114", ["D"]),
        ])},
        {"discovery_ms": signal_ms - 1000, "discovery": discovery("miami", [
            evt("KXTEMPMIAH-26SEP2113", ["A", "B", "C"]),
            evt("KXTEMPMIAH-26SEP2114", ["D"]),
        ])},
    ]
    snap = m.matching_event_snapshot(cycles, "miami", event)
    assert snap["event_ticker"] == "KXTEMPMIAH-26SEP2113"
    assert snap["market_tickers"] == ["A", "B", "C"]
    assert snap["event_target_at_ms"] == epoch_ms("2026-09-21T17:00:00Z")
    assert snap["horizon_to_settlement_ms"] == epoch_ms("2026-09-21T17:00:00Z") - signal_ms


def test_past_target_and_post_signal_discovery_are_ignored():
    signal_ms = epoch_ms("2026-09-21T17:00:05Z")
    event = {"city": "miami", "kwi_t": epoch_ms("2026-09-21T16:59:00Z"), "available_at_ms": signal_ms}
    cycles = [
        {"discovery_ms": signal_ms - 1000, "discovery": discovery("miami", [
            evt("KXTEMPMIAH-26SEP2113", ["PAST"]),
        ])},
        {"discovery_ms": signal_ms + 1000, "discovery": discovery("miami", [
            evt("KXTEMPMIAH-26SEP2114", ["TOO_LATE"]),
        ])},
    ]
    assert m.matching_event_snapshot(cycles, "miami", event) is None


def test_missing_future_event_fails_closed():
    signal_ms = epoch_ms("2026-09-21T17:00:05Z")
    event = {
        "city": "miami",
        "kwi_t": epoch_ms("2026-09-21T16:59:00Z"),
        "available_at_ms": signal_ms,
        "kind": "first_decision_eligible",
    }
    result = m.composite_result(event, None, [], window_ms=30000)
    assert result["status"] == m.UNPROVEN_REACTION
    assert "NO_PRE_SIGNAL_FUTURE_HOURLY_EVENT_DISCOVERY" in result["reasons"]
    assert result["bucket_count"] == 0


if __name__ == "__main__":
    tests = [
        test_ticker_hour_is_exact_eastern_market_time,
        test_nearest_future_pre_signal_event_is_selected,
        test_past_target_and_post_signal_discovery_are_ignored,
        test_missing_future_event_fails_closed,
    ]
    for test in tests:
        test()
    print(f"E401_SYNC_LINKER_TESTS_PASS {len(tests)}")
