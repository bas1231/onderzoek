"""Read-only deterministic build-ledger preflight regression coverage."""
from __future__ import annotations

import json
import unittest

from control.independent_continuity.diagnose_ledger import verify_bytes


def sample():
    return {
        "schema": "PREDICTION_BUILD_LOG_EVENT_V1",
        "event_id": "E001",
        "work_item_id": "A2Z-SYSTEMTEST",
        "created_at_utc": "2026-10-08T17:00:00Z",
        "event_type": "RESULT",
        "work_item_status": "IN_PROGRESS",
        "outcome": "PASS",
    }


class LedgerFaultTests(unittest.TestCase):
    def test_valid_event(self):
        self.assertIsNone(verify_bytes("E001.json", json.dumps(sample()).encode()))

    def test_filename_mismatch(self):
        self.assertEqual(verify_bytes("E002.json", json.dumps(sample()).encode()),
                         "event_id_filename_mismatch")

    def test_bad_json(self):
        self.assertEqual(verify_bytes("E001.json", b"{"), "invalid_json")

    def test_missing_timestamp(self):
        val = sample()
        val.pop("created_at_utc")
        self.assertEqual(verify_bytes("E001.json", json.dumps(val).encode()),
                         "missing_created_at_utc")

    def test_reject_naive_timestamp(self):
        val = sample()
        val["created_at_utc"] = "2026-10-08T17:00:00"
        self.assertEqual(verify_bytes("E001.json", json.dumps(val).encode()),
                         "naive_created_at_utc")

    def test_invalid_event_type(self):
        val = sample()
        val["event_type"] = "UNTRUSTED"
        self.assertEqual(verify_bytes("E001.json", json.dumps(val).encode()),
                         "invalid_event_type")

    def test_path_rejected(self):
        self.assertEqual(verify_bytes("../E001.json", json.dumps(sample()).encode()),
                         "unexpected_filename")


if __name__ == "__main__":
    unittest.main()
