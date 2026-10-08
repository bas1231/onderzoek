"""No-bridge regression tests for the independent continuity observer."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from control.independent_continuity.observer import scan, utc, write_immutable

NOW = datetime(2026, 10, 8, 18, 0, tzinfo=timezone.utc)


def event(event_id="E001", *, type="ATTEMPT", outcome="STARTED", status="IN_PROGRESS",
          minutes_old=60, work_item="TEST-WORK", first=None, next_action="diagnose"):
    return {
        "schema": "PREDICTION_BUILD_LOG_EVENT_V1",
        "event_id": event_id, "work_item_id": work_item,
        "created_at_utc": (NOW - timedelta(minutes=minutes_old)).isoformat().replace("+00:00", "Z"),
        "event_type": type, "work_item_status": status, "outcome": outcome,
        "first_incomplete_step": first, "next_action": next_action,
        "task_ids": ["TASK-ORIGINAL"],
    }


def store(folder: Path, obj: dict):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / (obj["event_id"] + ".json")).write_text(json.dumps(obj), encoding="utf-8")


class ObserverTest(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.events = self.root / "events"
        self.events.mkdir()
        self.proposals = self.root / "proposals"

    def run_scan(self):
        return scan(self.events, self.proposals, NOW, 30)

    def test_no_activity_is_not_an_authorized_retry(self):
        store(self.events, event())
        result = self.run_scan()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(result["observations"]), 1)
        obs = result["observations"][0]
        self.assertEqual(obs["classification"], "UNVERIFIED_TASK_OR_DISPATCH")
        self.assertFalse(obs["execution_authorized"])
        self.assertFalse(obs["automatic_resubmission"])
        self.assertEqual(obs["last_task_ids"], ["TASK-ORIGINAL"])

    def test_handoff_preserves_first_incomplete_step(self):
        store(self.events, event(type="RESULT", outcome="PASS", first="Astra post-build review"))
        obs = self.run_scan()["observations"][0]
        self.assertEqual(obs["classification"], "HANDOFF_REVIEW_REQUIRED")
        self.assertEqual(obs["first_incomplete_step"], "Astra post-build review")
        self.assertFalse(obs["execution_authorized"])

    def test_unresolved_pass_without_next_step_fails_closed(self):
        store(self.events, event(type="RESULT", outcome="PASS", next_action=""))
        self.assertEqual(self.run_scan()["observations"][0]["classification"], "MISSING_NEXT_STEP")

    def test_failed_result_requires_diagnosis(self):
        store(self.events, event(type="RESULT", outcome="FAIL"))
        self.assertEqual(self.run_scan()["observations"][0]["classification"], "FAILED_NEEDS_DIAGNOSIS")

    def test_blocked_or_done_are_not_resumed(self):
        store(self.events, event(event_id="E001", status="BLOCKED"))
        store(self.events, event(event_id="E002", status="DONE", work_item="SECOND"))
        self.assertEqual(self.run_scan()["observations"], [])

    def test_recent_progress_does_not_alarm(self):
        store(self.events, event(minutes_old=5))
        self.assertEqual(self.run_scan()["observations"], [])

    def test_note_does_not_reset_stall_clock(self):
        store(self.events, event(minutes_old=60))
        store(self.events, event(event_id="E002", type="NOTE", minutes_old=1))
        self.assertEqual(self.run_scan()["observations"][0]["last_substantive_event_id"], "E001")

    def test_latest_terminal_outcome_wins(self):
        store(self.events, event(minutes_old=60))
        store(self.events, event(event_id="E002", type="CLOSE", status="DONE", minutes_old=2))
        self.assertEqual(self.run_scan()["observations"], [])

    def test_future_timestamp_fails_closed(self):
        store(self.events, event(minutes_old=-60))
        self.assertEqual(self.run_scan()["observations"][0]["classification"], "CLOCK_OR_SNAPSHOT_ERROR")

    def test_immutable_proposals_are_idempotent(self):
        store(self.events, event())
        first = self.run_scan()
        self.assertEqual(len(first["new_report_files"]), 1)
        self.assertEqual(self.run_scan()["new_report_files"], [])

    def test_collision_not_overwritten(self):
        store(self.events, event())
        first = self.run_scan()
        path = self.proposals / first["new_report_files"][0]
        path.write_text("tampered")
        with self.assertRaisesRegex(ValueError, "collision"):
            self.run_scan()

    def test_malformed_newer_event_blocks_all_suggestions(self):
        store(self.events, event())
        (self.events / "BAD.json").write_text("{ not valid")
        result = self.run_scan()
        self.assertEqual(result["status"], "INPUT_INVALID")
        self.assertEqual(result["observations"], [])
        self.assertEqual(result["new_report_files"], [])

    def test_symlink_event_is_rejected(self):
        store(self.events, event())
        (self.events / "EVIL.json").symlink_to(self.events / "E001.json")
        self.assertEqual(self.run_scan()["status"], "INPUT_INVALID")

    def test_event_filename_must_match_identity(self):
        store(self.events, event())
        wrong = event(event_id="WRONG")
        (self.events / "E002.json").write_text(json.dumps(wrong))
        self.assertEqual(self.run_scan()["status"], "INPUT_INVALID")

    def test_naive_time_disallowed(self):
        with self.assertRaises(ValueError):
            utc("2026-10-08T18:00:00")

    def test_no_hidden_runtime_side_effects(self):
        self.assertEqual(list(self.root.iterdir()), [self.events])
        self.run_scan()
        self.assertTrue(self.proposals.is_dir())
        self.assertFalse((self.root / "bridge").exists())
        self.assertFalse((self.root / "executor").exists())


if __name__ == "__main__":
    unittest.main()
