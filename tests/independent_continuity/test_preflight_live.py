"""Read-only preflight must never start recovery, even with a live launcher."""
from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from control.independent_continuity.coordinator import UnsafeLaunch
from control.independent_continuity.preflight_live import assess

NOW = 1791487000.0


class LivePreflightTests(unittest.TestCase):
    def setUp(self):
        t = TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.home = Path(t.name)
        self.state = self.home / ".local/state/prediction-project-executor/independent-continuity"
        self.mirror = self.home / ".local/share/prediction-command-bus/repo/.git"
        self.bridge = self.home / ".local/share/prediction-chat-bridge"
        for path in (
            self.state, self.mirror, self.bridge / "routes",
            self.bridge / "sent", self.bridge / "dashboard_launchers",
        ):
            path.mkdir(parents=True, exist_ok=True)
        self.put(self.state / "scope.json", {
            "schema": "PREDICTION_INDEPENDENT_CONTINUITY_SCOPE_V1",
            "mode": "observe", "work_item_ids": ["TEST-ONLY"], "stale_minutes": 90,
            "live_trading": False, "paid_actions": False, "wallet_actions": False,
        })
        f = self.mirror / "FETCH_HEAD"
        f.write_text("0000000000000000000000000000000000000000")
        os.utime(f, (NOW, NOW))
        self.put(self.bridge / "sent" / "one.json",
                 {"task_id": "SESSION-ROUTE-001", "event_id": "one"})
        self.put(self.bridge / "routes" / "SESSION-ROUTE-001.json", {
            "chat_id": "CHAT-123", "consumer_id": "CONSUMER-123",
            "task_id": "SESSION-ROUTE-001",
        })
        self.put(self.bridge / "dashboard_launchers" / "one.json", {
            "schema": "PREDICTION_DASHBOARD_LAUNCHER_V1",
            "chat_id": "CHAT-123", "consumer_id": "CONSUMER-123",
            "updated_at_unix": NOW,
            "launch_base_url": "https://chatgpt.com/g/g-p-prediction-project",
            "capabilities": ["dashboard_new_session_launch_v1"],
        })

    @staticmethod
    def put(path, value):
        path.write_text(json.dumps(value), encoding="utf-8")

    def inspect_tree(self):
        return sorted(
            str(p.relative_to(self.home)) + (":" + p.read_text(encoding="utf-8")
                                             if p.is_file() else "")
            for p in self.home.rglob("*")
        )

    def test_ready_is_read_only_no_claim_no_launch(self):
        before = self.inspect_tree()
        result = assess(self.home, now_unix=NOW)
        self.assertEqual(result["status"], "READY_READ_ONLY")
        self.assertFalse(result["new_chat_launched"])
        self.assertFalse(result["auto_continue_enabled"])
        self.assertEqual(result["write_events"], 0)
        self.assertEqual(before, self.inspect_tree())

    def test_missing_live_launcher_blocks(self):
        (self.bridge / "dashboard_launchers" / "one.json").unlink()
        with self.assertRaisesRegex(UnsafeLaunch, "LAUNCHER_NOT_READY"):
            assess(self.home, now_unix=NOW)

    def test_disabled_or_emit_config_blocks(self):
        f = self.state / "scope.json"
        for mode in ("disabled", "emit"):
            value = json.loads(f.read_text(encoding="utf-8"))
            value["mode"] = mode
            self.put(f, value)
            with self.assertRaisesRegex(UnsafeLaunch, "REQUIRES_OBSERVE"):
                assess(self.home, now_unix=NOW)

    def test_stale_git_fetch_blocks(self):
        f = self.mirror / "FETCH_HEAD"
        os.utime(f, (NOW - 400, NOW - 400))
        with self.assertRaisesRegex(UnsafeLaunch, "stale"):
            assess(self.home, now_unix=NOW)

    def test_unproven_latest_chat_blocks(self):
        self.put(self.bridge / "sent" / "two.json",
                 {"task_id": "SESSION-ROUTE-002", "event_id": "two"})
        self.put(self.bridge / "routes" / "SESSION-ROUTE-002.json", {
            "chat_id": "CHAT-NEW", "consumer_id": "CONSUMER-NEW",
            "task_id": "SESSION-ROUTE-002",
        })
        os.utime(self.bridge / "sent" / "one.json", (NOW - 20, NOW - 20))
        os.utime(self.bridge / "sent" / "two.json", (NOW, NOW))
        with self.assertRaisesRegex(UnsafeLaunch, "LAUNCHER_NOT_READY"):
            assess(self.home, now_unix=NOW)

    def test_paid_flag_blocks(self):
        f = self.state / "scope.json"
        value = json.loads(f.read_text(encoding="utf-8"))
        value["paid_actions"] = True
        self.put(f, value)
        with self.assertRaisesRegex(UnsafeLaunch, "UNSAFE_SCOPE"):
            assess(self.home, now_unix=NOW)


if __name__ == "__main__":
    unittest.main()
