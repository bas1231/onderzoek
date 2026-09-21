#!/usr/bin/env python3
import unittest
from decimal import Decimal

from market_reaction import (
    MarketState, OrderBook, analyze_reaction, extract_kwi_events,
    REACTION_OBSERVED, NO_REACTION_OBSERVED_WITHIN_WINDOW, UNPROVEN_REACTION,
)


def st(ms, bid="0.40", ask="0.42", qty="10", transport="test"):
    return MarketState(
        ticker="KXTEMP-X", ts_ms=ms,
        yes_bid=Decimal(bid), yes_ask=Decimal(ask),
        no_bid=Decimal(str(1 - float(ask))), no_ask=Decimal(str(1 - float(bid))),
        yes_bid_qty=Decimal(qty), no_bid_qty=Decimal("9"), transport=transport,
    )


class MarketReactionTests(unittest.TestCase):
    def setUp(self):
        self.kwi = {"city":"miami","kwi_t":101,"signal_v":"81","kind":"first_decision_eligible","available_at_ms":10_000}

    def test_immediate_book_reaction(self):
        r = analyze_reaction(self.kwi, [st(9_000), st(10_100,"0.45","0.47"), st(40_000,"0.45","0.47")], window_ms=30_000, max_state_gap_ms=40_000)
        self.assertEqual((r["status"], r["latency_ms"]), (REACTION_OBSERVED, 100))

    def test_delayed_book_reaction(self):
        states=[st(9_000),st(11_000),st(14_000),st(16_000,"0.41","0.43"),st(40_000,"0.41","0.43")]
        r=analyze_reaction(self.kwi,states,window_ms=30_000,max_state_gap_ms=30_000)
        self.assertEqual((r["status"],r["latency_ms"]),(REACTION_OBSERVED,6_000))

    def test_no_reaction_with_full_coverage(self):
        r=analyze_reaction(self.kwi,[st(9_000),st(15_000),st(25_000),st(40_000)],window_ms=30_000,max_state_gap_ms=15_000)
        self.assertEqual(r["status"],NO_REACTION_OBSERVED_WITHIN_WINDOW)

    def test_gap_straddling_kwi_is_unproven(self):
        r=analyze_reaction(self.kwi,[st(9_000),st(11_000),st(40_000)],gaps=[{"start":9.5,"end":10.5}],window_ms=30_000,max_state_gap_ms=40_000)
        self.assertEqual(r["status"],UNPROVEN_REACTION)
        self.assertIn("CAPTURE_GAP_STRADDLES_WINDOW",r["reasons"])

    def test_out_of_order_is_unproven(self):
        r=analyze_reaction(self.kwi,[st(9_000),st(12_000),st(11_000),st(40_000)],window_ms=30_000,max_state_gap_ms=40_000)
        self.assertEqual(r["status"],UNPROVEN_REACTION)
        self.assertIn("OUT_OF_ORDER_MARKET_STATE",r["reasons"])

    def test_missing_post_coverage_is_unproven(self):
        r=analyze_reaction(self.kwi,[st(9_000),st(15_000)],window_ms=30_000,max_state_gap_ms=20_000)
        self.assertEqual(r["status"],UNPROVEN_REACTION)
        self.assertIn("CAPTURE_ENDS_BEFORE_WINDOW",r["reasons"])

    def test_ws_quiet_book_uses_recent_coverage(self):
        r=analyze_reaction(self.kwi,[st(1_000,transport="ws")],coverage_ms=[9_500,40_000],window_ms=30_000)
        self.assertEqual(r["status"],NO_REACTION_OBSERVED_WITHIN_WINDOW)

    def test_ws_old_snapshot_without_recent_coverage_is_unproven(self):
        r=analyze_reaction(self.kwi,[st(1_000,transport="ws")],coverage_ms=[40_000],window_ms=30_000)
        self.assertEqual(r["status"],UNPROVEN_REACTION)
        self.assertIn("PRE_EVENT_WS_COVERAGE_TOO_OLD",r["reasons"])

    def test_trade_counts_as_reaction(self):
        trades=[{"ticker":"KXTEMP-X","created_time":"1970-01-01T00:00:15+00:00","trade_id":"t1"}]
        r=analyze_reaction(self.kwi,[st(9_000),st(12_000),st(40_000)],trades,window_ms=30_000,max_state_gap_ms=30_000)
        self.assertEqual((r["status"],r["reaction_kind"],r["latency_ms"]),(REACTION_OBSERVED,"trade",5_000))

    def test_first_eligible_and_same_t_revision(self):
        prev={"t":100,"v":79,"contributors":2}
        manifests=[
            {"retrieved_at":"2026-09-21T10:00:00Z","cities":[{"city":"miami","config_version":"c1","latest_complete":prev,"latest_incomplete":{"t":101,"stations":[{"temp_f":80},{"temp_f":82}]}}]},
            {"retrieved_at":"2026-09-21T10:00:01Z","cities":[{"city":"miami","config_version":"c1","latest_complete":prev,"latest_incomplete":{"t":101,"stations":[{"temp_f":80},{"temp_f":82}]}}]},
            {"retrieved_at":"2026-09-21T10:00:02Z","cities":[{"city":"miami","config_version":"c1","latest_complete":prev,"latest_incomplete":{"t":101,"stations":[{"temp_f":81},{"temp_f":82}]}}]},
        ]
        ev=extract_kwi_events(manifests,"miami")
        self.assertEqual([x["kind"] for x in ev],["first_decision_eligible","revision"])
        self.assertEqual(ev[0]["signal_v"],"81")
        self.assertEqual(ev[1]["prior_station_values"],["80","82"])

    def test_requires_full_expected_station_set(self):
        manifests=[{"retrieved_at":"2026-09-21T10:00:00Z","cities":[{"city":"miami","latest_complete":{"t":100,"v":79,"contributors":3},"latest_incomplete":{"t":101,"stations":[{"temp_f":80},{"temp_f":82}]}}]}]
        self.assertEqual(extract_kwi_events(manifests,"miami"),[])

    def test_ws_sequence_gap_fails_closed(self):
        ob=OrderBook("KXTEMP-X")
        ob.snapshot({"type":"orderbook_snapshot","seq":2,"msg":{"market_ticker":"KXTEMP-X","yes_dollars_fp":[["0.40","10"]],"no_dollars_fp":[["0.58","8"]]}},9)
        bad={"type":"orderbook_delta","seq":4,"msg":{"market_ticker":"KXTEMP-X","side":"yes","price_dollars":"0.40","delta_fp":"-1"}}
        with self.assertRaisesRegex(ValueError,"sequence gap"):
            ob.delta(bad,10)

    def test_deterministic_replay(self):
        states=[st(9_000),st(11_000),st(15_000,"0.44","0.46"),st(40_000,"0.44","0.46")]
        a=analyze_reaction(self.kwi,states,window_ms=30_000,max_state_gap_ms=30_000)
        b=analyze_reaction(self.kwi,states,window_ms=30_000,max_state_gap_ms=30_000)
        self.assertEqual(a,b)


if __name__ == "__main__":
    unittest.main()
