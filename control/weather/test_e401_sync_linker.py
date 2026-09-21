#!/usr/bin/env python3
from datetime import datetime, timezone
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control" / "weather"))

import e401_sync_linker as m


def epoch_s(iso: str) -> int:
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())


def test_event_ticker_matches_city_local_hour():
    target = epoch_s("2026-09-21T16:00:00Z")
    assert m.event_matches_target("miami", "KXTEMPMIAH-26SEP2112", target)
    assert m.event_matches_target("nyc", "KXTEMPNYCH-26SEP2112", target)
    assert not m.event_matches_target("miami", "KXTEMPMIAH-26SEP2111", target)


def test_chicago_uses_central_local_hour():
    target = epoch_s("2026-09-21T16:00:00Z")
    assert m.event_matches_target("chicago", "KXTEMPCHIH-26SEP2111", target)
    assert not m.event_matches_target("chicago", "KXTEMPCHIH-26SEP2112", target)


def test_latest_pre_signal_discovery_wins_and_future_is_ignored():
    target = epoch_s("2026-09-21T16:00:00Z")
    signal_ms = epoch_s("2026-09-21T15:59:55Z") * 1000
    event = {"city": "miami", "kwi_t": target, "available_at_ms": signal_ms}

    def discovery(tickers):
        return {
            "series": [{
                "city": "miami",
                "events": [{
                    "event_ticker": "KXTEMPMIAH-26SEP2112",
                    "market_tickers": tickers,
                }],
            }]
        }

    cycles = [
        {"discovery_ms": signal_ms - 5000, "discovery": discovery(["A", "B"])},
        {"discovery_ms": signal_ms - 1000, "discovery": discovery(["A", "B", "C"])},
        {"discovery_ms": signal_ms + 1000, "discovery": discovery(["FUTURE_ONLY"])},
    ]
    snap = m.matching_event_snapshot(cycles, "miami", event)
    assert snap["event_ticker"] == "KXTEMPMIAH-26SEP2112"
    assert snap["market_tickers"] == ["A", "B", "C"]


def test_missing_pre_signal_event_fails_closed():
    target = epoch_s("2026-09-21T16:00:00Z")
    signal_ms = epoch_s("2026-09-21T15:59:55Z") * 1000
    event = {
        "city": "miami",
        "kwi_t": target,
        "available_at_ms": signal_ms,
        "kind": "first_decision_eligible",
    }
    result = m.composite_result(event, None, [], window_ms=30000)
    assert result["status"] == m.UNPROVEN_REACTION
    assert "NO_MATCHING_PRE_SIGNAL_HOURLY_EVENT_DISCOVERY" in result["reasons"]
    assert result["bucket_count"] == 0


if __name__ == "__main__":
    tests = [
        test_event_ticker_matches_city_local_hour,
        test_chicago_uses_central_local_hour,
        test_latest_pre_signal_discovery_wins_and_future_is_ignored,
        test_missing_pre_signal_event_fails_closed,
    ]
    for test in tests:
        test()
    print(f"E401_SYNC_LINKER_TESTS_PASS {len(tests)}")
