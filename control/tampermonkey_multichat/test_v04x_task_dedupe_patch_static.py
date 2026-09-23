#!/usr/bin/env python3
"""Static regression guard for v0.4.x task-level RESULT_READY dedupe.

The canonical checked-in userscript is intentionally still v0.3.3 because the
browser/local checkout advanced through patch files.  This test therefore guards
the patch chain itself: v0.4.5 must add persistent task-id delivery memory and
use it before submitting, and v0.4.6 must preserve that contract while adding
its retry/page guards.
"""
from pathlib import Path
import re
import unittest

HERE = Path(__file__).resolve().parent
V045 = HERE / "patch_v045_delivery_dedupe.py"
V046 = HERE / "patch_v046_delivery_guard.py"


class V04xTaskDedupePatchStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v045 = V045.read_text(encoding="utf-8")
        cls.v046 = V046.read_text(encoding="utf-8")

    def test_v045_adds_persistent_task_delivery_memory(self):
        self.assertIn(
            "const KEY_SENT_TASKS = 'prediction_sent_tasks_v045';",
            self.v045,
        )
        self.assertIn(
            "(taskKey && remembered(KEY_SENT_TASKS, taskKey))",
            self.v045,
        )

    def test_v045_dedupes_same_task_before_submit(self):
        block = re.search(
            r"const alreadyDelivered =(?P<body>.*?)status\(`event \$\{taskKey \|\| event\.event_id\}`\);",
            self.v045,
            re.S,
        )
        self.assertIsNotNone(block)
        body = block.group("body")
        self.assertIn("remembered(KEY_SENT_EVENTS, event.event_id)", body)
        self.assertIn("remembered(KEY_SENT_TASKS, taskKey)", body)
        self.assertIn("recentUserTurnContainsDelivery(String(event.message))", body)
        self.assertIn("await ack(event.event_id, identity.chatId, identity.consumerId)", body)
        self.assertIn("continue;", body)
        self.assertNotIn("submitMessage", body)

    def test_v045_remembers_task_before_normal_ack(self):
        remember = self.v045.find("if (taskKey) remember(KEY_SENT_TASKS, taskKey);")
        ack = self.v045.find(
            "const ok = await ack(event.event_id, identity.chatId, identity.consumerId);",
            remember,
        )
        self.assertGreaterEqual(remember, 0)
        self.assertGreater(ack, remember)

    def test_v046_is_incremental_on_v045_and_preserves_task_key_path(self):
        self.assertIn("Patch Prediction Chat Wake Bridge v0.4.5 -> v0.4.6", self.v046)
        self.assertIn("const retryKey = taskKey || String(event.event_id);", self.v046)
        self.assertIn("deliveryRetryAfter.delete(taskKey || String(event.event_id));", self.v046)
        # v0.4.6 must not introduce any replacement/deletion of task-memory symbols.
        self.assertNotIn("KEY_SENT_TASKS =", self.v046)
        self.assertNotIn("KEY_SENT_TASKS, []", self.v046)

    def test_result_ready_anchor_is_task_identity_based(self):
        self.assertIn("RESULT_READY:", self.v045)
        self.assertRegex(
            self.v045,
            r"RESULT_READY:\\s\*\(\[A-Za-z0-9\._:-\]\{1,160\}\)",
        )


if __name__ == "__main__":
    unittest.main()
