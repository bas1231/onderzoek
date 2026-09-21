from decimal import Decimal

from control.weather.kwi_market_reaction_e401 import (
    MarketState, OrderBook, analyze_reaction, extract_kwi_events,
    REACTION_OBSERVED, NO_REACTION_OBSERVED_WITHIN_WINDOW, UNPROVEN_REACTION,
)


def s(ts, bid="0.50", ask="0.51", transport="ws", seq=None):
    return MarketState("KXTEMP-X", ts, bid, ask, "0.49", "0.50", "10", "10", transport, seq)


def test_direct_reaction():
    ev={"available_at_ms":10000}
    states=[s(9000), s(11000, bid="0.55")]
    out=analyze_reaction(ev, states, coverage_ms=[10000,11000], window_ms=5000)
    assert out["status"]==REACTION_OBSERVED
    assert out["latency_ms"]==1000


def test_delayed_reaction():
    ev={"available_at_ms":10000}
    states=[s(9000), s(12000), s(14000, bid="0.55")]
    out=analyze_reaction(ev, states, coverage_ms=[10000,12000,14000,15000], window_ms=5000)
    assert out["status"]==REACTION_OBSERVED
    assert out["latency_ms"]==4000


def test_no_reaction_with_coverage():
    ev={"available_at_ms":10000}
    states=[s(9000), s(12000), s(15000)]
    out=analyze_reaction(ev, states, coverage_ms=[10000,15000], window_ms=5000)
    assert out["status"]==NO_REACTION_OBSERVED_WITHIN_WINDOW


def test_capture_gap_fails_closed():
    ev={"available_at_ms":10000}
    states=[s(9000), s(12000, bid="0.55")]
    out=analyze_reaction(ev, states, gaps=[{"start":9500,"end":10500}], coverage_ms=[10000,12000], window_ms=5000)
    assert out["status"]==UNPROVEN_REACTION
    assert "CAPTURE_GAP_STRADDLES_WINDOW" in out["reasons"]


def test_out_of_order_fails_closed():
    ev={"available_at_ms":10000}
    out=analyze_reaction(ev, [s(11000), s(9000)], coverage_ms=[10000,11000], window_ms=5000)
    assert out["status"]==UNPROVEN_REACTION
    assert "OUT_OF_ORDER_MARKET_STATE" in out["reasons"]


def test_capture_ends_before_window_fails_closed():
    ev={"available_at_ms":10000}
    out=analyze_reaction(ev, [s(9000), s(12000)], coverage_ms=[10000,12000], window_ms=5000)
    assert out["status"]==UNPROVEN_REACTION
    assert "CAPTURE_ENDS_BEFORE_WINDOW" in out["reasons"]


def test_trade_counts_as_reaction():
    ev={"available_at_ms":10000}
    states=[s(9000), s(15000)]
    trades=[{"ticker":"KXTEMP-X","ts_ms":11500,"yes_price_dollars":"0.52"}]
    out=analyze_reaction(ev, states, trades=trades, coverage_ms=[10000,15000], window_ms=5000)
    assert out["status"]==REACTION_OBSERVED
    assert out["reaction_kind"]=="trade"
    assert out["latency_ms"]==1500


def test_revision_not_duplicate_first_signal():
    manifests=[
      {"retrieved_at":"2026-09-21T10:00:00+00:00","cities":[{"city":"miami","config_version":"v1","latest_complete":{"t":1,"v":80,"contributors":2},"latest_incomplete":{"t":2,"stations":[{"temp_f":81},{"temp_f":83}]}}]},
      {"retrieved_at":"2026-09-21T10:00:01+00:00","cities":[{"city":"miami","config_version":"v1","latest_complete":{"t":1,"v":80,"contributors":2},"latest_incomplete":{"t":2,"stations":[{"temp_f":81},{"temp_f":84}]}}]},
    ]
    rows=extract_kwi_events(manifests,"miami")
    assert [r["kind"] for r in rows]==["first_decision_eligible","revision"]
    assert rows[0]["signal_v"]=="82"


def test_rest_parser_complements_yes_no_books():
    from control.weather.kwi_market_reaction_e401 import market_state_from_rest
    state=market_state_from_rest("KXTEMP-X",10000,{"orderbook_fp":{"yes_dollars":[["0.48","3"],["0.50","2"]],"no_dollars":[["0.47","4"],["0.49","5"]]}})
    assert state.yes_bid==Decimal("0.50")
    assert state.yes_ask==Decimal("0.51")
    assert state.no_bid==Decimal("0.49")
    assert state.no_ask==Decimal("0.50")


def test_ws_sequence_gap_fails_closed_and_invalidates_book():
    ob=OrderBook("KXTEMP-X")
    ob.snapshot({"type":"orderbook_snapshot","seq":10,"msg":{"market_ticker":"KXTEMP-X","yes_dollars_fp":[["0.50","10"]],"no_dollars_fp":[["0.49","10"]]}},10000)
    try:
        ob.delta({"type":"orderbook_delta","seq":12,"msg":{"market_ticker":"KXTEMP-X","side":"yes","price_dollars":"0.50","delta_fp":"-1"}},11000)
    except ValueError as e:
        assert "sequence gap" in str(e)
        assert ob.ready is False
    else:
        raise AssertionError("sequence gap should fail closed")


def test_deterministic_replay():
    ev={"available_at_ms":10000}
    states=[s(9000), s(11000, bid="0.55")]
    a=analyze_reaction(ev, states, coverage_ms=[10000,11000,15000], window_ms=5000)
    b=analyze_reaction(ev, states, coverage_ms=[10000,11000,15000], window_ms=5000)
    assert a==b
