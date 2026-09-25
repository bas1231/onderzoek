#!/usr/bin/env python3
import io
import json
import unittest

from kalshi_market_reaction_ws import handle_message
from market_reaction import OrderBook


def rows(fp):
    return [json.loads(line) for line in fp.getvalue().splitlines() if line.strip()]


class MarketReactionWsTests(unittest.TestCase):
    def setUp(self):
        self.sequence = {}
        self.ticker = "KXTEMP-X"
        self.books = {self.ticker: OrderBook(self.ticker)}
        self.ts = "2026-09-21T12:00:00+00:00"

    def snapshot(self, seq=1):
        return {
            "type": "orderbook_snapshot",
            "sid": 1,
            "seq": seq,
            "msg": {
                "market_ticker": self.ticker,
                "yes_dollars_fp": [["0.40", "10"]],
                "no_dollars_fp": [["0.58", "8"]],
            },
        }

    def test_every_decoded_frame_emits_transport_coverage(self):
        fp = io.StringIO()
        handle_message(self.books, {"type": "subscribed", "sid": 1, "msg": {}}, self.ts, fp, self.sequence)
        kinds = [r["kind"] for r in rows(fp)]
        self.assertEqual(kinds, ["coverage", "ws_raw"])

    def test_snapshot_emits_coverage_raw_and_state(self):
        fp = io.StringIO()
        handle_message(self.books, self.snapshot(), self.ts, fp, self.sequence)
        out = rows(fp)
        self.assertEqual([r["kind"] for r in out], ["coverage", "ws_raw", "market_state"])
        self.assertTrue(self.books[self.ticker].ready)
        self.assertEqual(out[-1]["yes_bid"], "0.40")

    def test_malformed_replacement_snapshot_resets_book(self):
        fp = io.StringIO()
        handle_message(self.books, self.snapshot(), self.ts, fp, self.sequence)
        bad = self.snapshot(seq=2)
        bad["msg"]["no_dollars_fp"] = [["not-a-price", "8"]]
        handle_message(self.books, bad, "2026-09-21T12:00:01+00:00", fp, self.sequence)
        out = rows(fp)
        self.assertEqual(out[-1]["kind"], "capture_gap")
        self.assertIn("snapshot_reconstruction", out[-1]["reason"])
        self.assertFalse(self.books[self.ticker].ready)

    def test_sequence_gap_aborts_capture(self):
        fp = io.StringIO()
        handle_message(self.books, self.snapshot(seq=10), self.ts, fp, self.sequence)
        bad_delta = {
            "type": "orderbook_delta",
            "sid": 1,
            "seq": 12,
            "msg": {
                "market_ticker": self.ticker,
                "side": "yes",
                "price_dollars": "0.40",
                "delta_fp": "-1",
            },
        }
        with self.assertRaisesRegex(ValueError, "sequence gap"):
            handle_message(self.books, bad_delta, "2026-09-21T12:00:01+00:00", fp, self.sequence)
        out = rows(fp)
        self.assertEqual(out[-1]["kind"], "capture_gap")
        self.assertIn("sequence gap", out[-1]["reason"])
        self.assertEqual(sum(r["kind"] == "market_state" for r in out), 1)

    def test_trade_frame_emits_coverage_and_trade(self):
        fp = io.StringIO()
        msg = {
            "type": "trade",
            "seq": 2,
            "msg": {"market_ticker": self.ticker, "trade_id": "t1"},
        }
        handle_message(self.books, msg, self.ts, fp, self.sequence)
        out = rows(fp)
        self.assertEqual([r["kind"] for r in out], ["coverage", "ws_raw", "trade"])
        self.assertEqual(out[-1]["trade_id"], "t1")


if __name__ == "__main__":
    unittest.main()
