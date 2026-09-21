#!/usr/bin/env python3
import unittest

from analyze_kwi_market_reaction import partition_kwi_events


class AnalyzeKwiMarketReactionTests(unittest.TestCase):
    def test_revisions_never_count_as_primary_samples(self):
        events = [
            {"kind": "first_decision_eligible", "city": "miami", "kwi_t": 1},
            {"kind": "revision", "city": "miami", "kwi_t": 1},
            {"kind": "revision", "city": "miami", "kwi_t": 1},
            {"kind": "first_decision_eligible", "city": "miami", "kwi_t": 2},
        ]
        primary, revisions, ignored = partition_kwi_events(events)
        self.assertEqual(len(primary), 2)
        self.assertEqual(len(revisions), 2)
        self.assertEqual(ignored, [])
        self.assertEqual([e["kwi_t"] for e in primary], [1, 2])

    def test_unknown_event_kind_fails_closed_outside_primary_sample(self):
        events = [
            {"kind": "first_decision_eligible", "kwi_t": 1},
            {"kind": "mystery", "kwi_t": 2},
            {},
            None,
        ]
        primary, revisions, ignored = partition_kwi_events(events)
        self.assertEqual(len(primary), 1)
        self.assertEqual(revisions, [])
        self.assertEqual(len(ignored), 3)


if __name__ == "__main__":
    unittest.main()
