#!/usr/bin/env python3
"""Offline regression tests for bridge_server_hardened.

No localhost service, credentials or external network are required.
"""
from __future__ import annotations

import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

h = importlib.import_module("bridge_server_hardened")


class HardenedBridgeTests(unittest.TestCase):
    def test_result_ready_is_compacted_and_bounded(self):
        raw = "RESULT_READY:\n=== WSL RESULT ===\nDEV_TASK_STATUS=PASS\nExit code: 0\n" + ("x" * 5000)
        out = h.compact_delivery_event({"event_id": "evt-1", "task_id": "task-1", "message": raw})
        self.assertTrue(out["delivery_compacted"])
        self.assertLessEqual(len(out["message"]), h.MAX_BROWSER_MESSAGE)
        self.assertIn("NIGHTSHIFT_WSL_RESULT_V1", out["message"])
        self.assertIn("task=task-1", out["message"])
        self.assertIn("status=PASS", out["message"])
        self.assertNotIn("x" * 100, out["message"])

    def test_normal_message_is_preserved(self):
        out = h.compact_delivery_event({"event_id": "evt-2", "task_id": "task-2", "message": "PING canary"})
        self.assertEqual(out["message"], "PING canary")

    def test_sent_task_duplicate_is_retired_before_delivery(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sent = root / "sent"
            outbox = root / "outbox"
            sent.mkdir(); outbox.mkdir()
            (sent / "old.json").write_text(json.dumps({"event_id": "old", "task_id": "same-task"}), encoding="utf-8")
            dup = outbox / "dup.json"
            dup.write_text(json.dumps({"event_id": "dup", "task_id": "same-task", "message": "RESULT_READY: stale"}), encoding="utf-8")
            fresh = outbox / "fresh.json"
            fresh.write_text(json.dumps({"event_id": "fresh", "task_id": "new-task", "message": "PING"}), encoding="utf-8")

            sequence = [(dup, json.loads(dup.read_text())), (fresh, json.loads(fresh.read_text()))]
            def oldest(*_args, **_kwargs):
                return sequence.pop(0) if sequence else (None, None)

            with patch.object(h.base, "SENT", sent), patch.object(h, "_RAW_OLDEST_EVENT", oldest), patch.object(h.base, "release_lease"):
                path, obj = h.hardened_oldest_event()

            self.assertEqual(path, fresh)
            self.assertEqual(obj["task_id"], "new-task")
            self.assertFalse(dup.exists())
            self.assertTrue((sent / "dup.json").exists())


if __name__ == "__main__":
    unittest.main()
