#!/usr/bin/env python3
import unittest

from summarize_kwi_market_reaction_e401 import (
    REACTION_OBSERVED,
    NO_REACTION_OBSERVED_WITHIN_WINDOW,
    UNPROVEN_REACTION,
    SUPPORTED_SCHEMA,
    summarize_reports,
)


def result(city, kwi_t, status=REACTION_OBSERVED, latency_ms=1000):
    row = {
        "status": status,
        "kwi_event": {"kind": "first_decision_eligible", "city": city, "kwi_t": kwi_t},
    }
    if status == REACTION_OBSERVED:
        row["latency_ms"] = latency_ms
    return row


def report(rows, schema=SUPPORTED_SCHEMA):
    return {
        "schema": schema,
        "primary_events_total": len(rows),
        "events_total": len(rows),
        "results": rows,
        "revision_results": [],
    }


class E401SummaryTests(unittest.TestCase):
    def test_minimum_evidence_can_pass_without_implying_edge(self):
        rows = []
        for i in range(15):
            rows.append(result("miami", i, latency_ms=100 + i))
            rows.append(result("chicago", i, NO_REACTION_OBSERVED_WITHIN_WINDOW))
        out = summarize_reports([report(rows)])
        self.assertTrue(out["minimum_evidence_met"])
        self.assertEqual(out["unique_primary_events"], 30)
        self.assertEqual(out["evaluable_city_count"], 2)
        self.assertEqual(out["economic_conclusion"], "NO_PROVEN_EDGE")
        self.assertEqual(out["next_gate"], "KAL-WX-ORDER-ARRIVAL-E402")

    def test_unproven_events_count_against_coverage(self):
        rows = [result("miami", i) for i in range(15)] + [result("chicago", i) for i in range(13)]
        rows += [result("chicago", 13, UNPROVEN_REACTION), result("chicago", 14, UNPROVEN_REACTION)]
        out = summarize_reports([report(rows)])
        self.assertEqual(out["unique_primary_events"], 30)
        self.assertEqual(out["evaluable_primary_events"], 28)
        self.assertLess(out["valid_synchronized_capture_fraction"], 0.95)
        self.assertFalse(out["minimum_evidence_met"])

    def test_identical_duplicates_do_not_inflate_sample(self):
        row = result("miami", 1)
        out = summarize_reports([report([row]), report([dict(row)])], minimum_events=2, minimum_cities=1)
        self.assertEqual(out["unique_primary_events"], 1)
        self.assertEqual(out["identical_duplicate_events_deduplicated"], 1)
        self.assertFalse(out["minimum_evidence_met"])

    def test_conflicting_duplicate_fails_dataset_integrity(self):
        a = result("miami", 1, latency_ms=100)
        b = result("miami", 1, latency_ms=200)
        out = summarize_reports([report([a]), report([b])], minimum_events=1, minimum_cities=1)
        self.assertFalse(out["checks"]["dataset_integrity_pass"])
        self.assertEqual(out["conflicting_duplicate_event_keys"], [["miami", "1"]])
        self.assertFalse(out["minimum_evidence_met"])

    def test_legacy_v1_report_never_counts(self):
        legacy = report([result("miami", 1)], schema="KAL_WX_MARKET_REACTION_E401_V1")
        out = summarize_reports([legacy], minimum_events=1, minimum_cities=1)
        self.assertEqual(out["unique_primary_events"], 0)
        self.assertEqual(len(out["rejected_reports"]), 1)
        self.assertFalse(out["minimum_evidence_met"])

    def test_unknown_or_malformed_primary_result_fails_integrity(self):
        bad = {"status": "UNKNOWN", "kwi_event": {"city": "miami", "kwi_t": 1}}
        out = summarize_reports([report([bad])], minimum_events=1, minimum_cities=1)
        self.assertEqual(out["invalid_primary_results"], 1)
        self.assertFalse(out["checks"]["dataset_integrity_pass"])
        self.assertFalse(out["minimum_evidence_met"])


if __name__ == "__main__":
    unittest.main()
