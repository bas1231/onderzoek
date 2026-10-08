"""Stand-alone periodic runner tests: fake mirror only, no real WSL state."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
from unittest.mock import patch
from tempfile import TemporaryDirectory
import unittest

from control.independent_continuity.runner import run
from control.independent_continuity.coordinator import UnsafeLaunch

NOW = datetime(2026, 10, 8, 20, tzinfo=timezone.utc)
EPOCH = NOW.timestamp()


class PeriodicRunnerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.repo = self.home / ".local/share/prediction-command-bus/repo"
        events = self.repo / "control/build_log/events"
        events.mkdir(parents=True)
        git = self.repo / ".git"
        git.mkdir(parents=True)
        (git / "FETCH_HEAD").write_text("snapshot marker")
        os.utime(git / "FETCH_HEAD", (EPOCH, EPOCH))
        self.event = {
            "schema": "PREDICTION_BUILD_LOG_EVENT_V1",
            "event_id": "E001", "work_item_id": "A2Z-ALLOWED",
            "created_at_utc": (NOW - timedelta(hours=3)).isoformat(),
            "event_type": "ATTEMPT", "work_item_status": "IN_PROGRESS",
            "outcome": "STARTED", "task_ids": ["T001"],
        }
        (events / "E001.json").write_text(json.dumps(self.event))
        snapshot_patch = patch("control.independent_continuity.runner.snapshot_events", self.fake_snapshot)
        snapshot_patch.start()
        self.addCleanup(snapshot_patch.stop)
        self.config = {
            "schema": "PREDICTION_INDEPENDENT_CONTINUITY_SCOPE_V1",
            "mode": "observe", "work_item_ids": ["A2Z-ALLOWED"],
            "stale_minutes": 90,
            "live_trading": False, "paid_actions": False, "wallet_actions": False,
        }

    def fake_snapshot(self, repo, destination):
        payload = (self.repo / "control/build_log/events/E001.json").read_bytes()
        (destination / "E001.json").write_bytes(payload)
        return {"source_commit": "a" * 40, "event_files": 1}

    def test_disabled_mode_does_not_read_or_write(self):
        cfg = dict(self.config, mode="disabled")
        self.assertEqual(run(cfg, home=self.home, now_unix=EPOCH)["status"], "DISABLED")
        self.assertFalse((self.home / ".local/state/prediction-project-executor").exists())

    def test_observe_without_browser_still_collects_proposals(self):
        state = run(self.config, home=self.home, now_unix=EPOCH)
        self.assertEqual(state["status"], "PASS")
        self.assertEqual(state["mode"], "observe")
        self.assertEqual(state["stale_observations"], 1)
        self.assertEqual(state["coordinator"]["state"], "OBSERVATION_ONLY")
        self.assertFalse(state["bridge_mutated"])
        p = self.home / ".local/state/prediction-project-executor/independent-continuity/proposals"
        self.assertEqual(len(list(p.glob("*.json"))), 1)
        self.assertFalse((self.home / ".local/share/prediction-chat-bridge").exists())

    def test_second_observation_is_stable(self):
        first = run(self.config, home=self.home, now_unix=EPOCH)
        later = run(self.config, home=self.home, now_unix=EPOCH + 30)
        self.assertEqual(first["fresh_proposals"], 1)
        self.assertEqual(later["fresh_proposals"], 0)

    def test_stale_mirror_never_creates_proposals(self):
        marker = self.repo / ".git/FETCH_HEAD"
        os.utime(marker, (EPOCH - 600, EPOCH - 600))
        with self.assertRaisesRegex(UnsafeLaunch, "stale"):
            run(self.config, home=self.home, now_unix=EPOCH)
        root = self.home / ".local/state/prediction-project-executor/independent-continuity"
        self.assertFalse(root.exists())

    def test_no_explicit_allowlist_fails_closed(self):
        with self.assertRaisesRegex(UnsafeLaunch, "work item"):
            run(dict(self.config, work_item_ids=[]), home=self.home, now_unix=EPOCH)

    def test_mode_emission_requires_live_dashboard_launcher(self):
        with self.assertRaises(UnsafeLaunch):
            run(dict(self.config, mode="emit"), home=self.home, now_unix=EPOCH)
        self.assertFalse((self.home / ".local/share/prediction-chat-bridge/outbox").exists())

    def test_fails_closed_if_paid_action_set(self):
        with self.assertRaisesRegex(UnsafeLaunch, "safety flags"):
            run(dict(self.config, paid_actions=True), home=self.home, now_unix=EPOCH)


if __name__ == "__main__":
    unittest.main()
