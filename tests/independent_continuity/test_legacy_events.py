"""Opaque historical build-ledger events must never authorize recovery.

These are intentionally NOT translated into canonical PLAN/RESULT/NOTE,
because their legacy schema semantics are not guaranteed.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from control.independent_continuity.observer import load_events, scan

NOW = datetime(2026, 10, 8, 19, tzinfo=timezone.utc)


def entry(ident, kind, minutes_old, item="A2Z-SYSTEMTEST-20261005", status="IN_PROGRESS"):
    return {
        "schema": "PREDICTION_BUILD_LOG_EVENT_V1",
        "event_id": ident,
        "work_item_id": item,
        "created_at_utc": (NOW - timedelta(minutes=minutes_old)).isoformat(),
        "event_type": kind,
        "outcome": "AWAITING_SCOPE_APPROVAL" if kind == "BLOCKER" else "WAITING_FOR_RUNTIME_EVIDENCE",
        "work_item_status": status,
        "task_ids": ["ORIGINAL-LEGACY-E045"],
    }


class LegacyEventBarrierTest(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.events = Path(self.tmp.name) / "events"
        self.events.mkdir()
        self.out = Path(self.tmp.name) / "out"

    def save(self, obj):
        (self.events / (obj["event_id"] + ".json")).write_text(json.dumps(obj), encoding="utf-8")

    def check(self):
        return scan(self.events, self.out, NOW, 30)

    def test_legacy_checkpoint_is_not_a_resume_signal(self):
        self.save(entry("20261005T2045Z-A2Z-RESUME-E045", "CHECKPOINT", 120))
        result = self.check()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["opaque_event_count"], 1)
        self.assertEqual(result["observations"], [])
        self.assertEqual(result["new_report_files"], [])

    def test_legacy_blocker_preserves_barrier(self):
        self.save(entry("20261005T2057Z-A2Z-COORDINATION-PROPOSAL", "BLOCKER", 110, status="BLOCKED"))
        self.assertEqual(self.check()["observations"], [])

    def test_newer_unknown_blocks_older_started_attempt(self):
        self.save(entry("OLD-E001", "ATTEMPT", 180))
        self.save(entry("LEGACY-E002", "CHECKPOINT", 120))
        result = self.check()
        self.assertEqual(result["observations"], [])
        self.assertEqual(result["opaque_event_count"], 1)

    def test_newer_explicit_valid_attempt_supersedes_older_opaque(self):
        self.save(entry("LEGACY-E001", "BLOCKER", 180, status="BLOCKED"))
        self.save(entry("NEW-E002", "ATTEMPT", 120))
        result = self.check()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(result["observations"]), 1)
        self.assertEqual(result["observations"][0]["last_substantive_event_id"], "NEW-E002")
        self.assertFalse(result["observations"][0]["execution_authorized"])

    def test_opaque_barrier_is_scoped_to_its_work_item(self):
        self.save(entry("LEGACY-A", "CHECKPOINT", 120))
        self.save(entry("CANON-B", "ATTEMPT", 120, item="OTHER-WORK"))
        result = self.check()
        self.assertEqual(len(result["observations"]), 1)
        self.assertEqual(result["observations"][0]["work_item_id"], "OTHER-WORK")

    def test_missing_identity_still_globally_invalid(self):
        obj = entry("MISSING-E001", "CHECKPOINT", 90)
        del obj["work_item_id"]
        self.save(obj)
        self.assertEqual(self.check()["status"], "INPUT_INVALID")
        self.assertEqual(self.check()["observations"], [])

    def test_malformed_json_still_globally_invalid(self):
        self.save(entry("VALID-E001", "ATTEMPT", 120, item="OTHER-WORK"))
        (self.events / "broken.json").write_text("{", encoding="utf-8")
        result = self.check()
        self.assertEqual(result["status"], "INPUT_INVALID")
        self.assertEqual(result["observations"], [])

    def test_missing_event_type_is_global_failure(self):
        obj = entry("BROKEN-E001", "BLOCKER", 120)
        del obj["event_type"]
        self.save(obj)
        self.assertEqual(self.check()["status"], "INPUT_INVALID")

    def test_symlink_rejected_with_legacy_present(self):
        self.save(entry("LEGACY-E001", "CHECKPOINT", 120))
        (self.events / "EVIL.json").symlink_to(self.events / "LEGACY-E001.json")
        self.assertEqual(self.check()["status"], "INPUT_INVALID")

    def test_legacy_type_does_not_override_newer_terminal_state(self):
        self.save(entry("OLD-E001", "BLOCKER", 180, status="BLOCKED"))
        self.save(entry("NEW-E002", "CLOSE", 120, status="DONE"))
        self.assertEqual(self.check()["observations"], [])

    def test_older_legacy_does_not_hide_newer_terminal_block(self):
        self.save(entry("OLD-E001", "CHECKPOINT", 180))
        self.save(entry("NEW-E002", "DECISION", 120, status="BLOCKED"))
        self.assertEqual(self.check()["observations"], [])

    def test_stable_repeated_legacy_snapshot(self):
        self.save(entry("OLD-E001", "CHECKPOINT", 180))
        first = self.check()
        second = self.check()
        self.assertEqual(first["status"], "PASS")
        self.assertEqual(second["status"], "PASS")
        self.assertEqual(first["new_report_files"], [])
        self.assertEqual(second["new_report_files"], [])


if __name__ == "__main__":
    unittest.main()
