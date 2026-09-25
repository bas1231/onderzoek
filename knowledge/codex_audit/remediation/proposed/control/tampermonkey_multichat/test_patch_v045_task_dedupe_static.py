#!/usr/bin/env python3
"""Static regression checks for v0.4.5 task-level RESULT_READY dedupe.

These checks intentionally validate the patch artifact rather than the stale
canonical userscript. The local/browser userscript advanced beyond main, so
this protects the known-good dedupe contract without overwriting local state.
"""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / "control" / "tampermonkey_multichat" / "patch_v045_delivery_dedupe.py"


class PatchV045TaskDedupeStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = PATCH.read_text(encoding="utf-8")

    def test_persistent_task_cache_is_added(self):
        self.assertIn("KEY_SENT_TASKS = 'prediction_sent_tasks_v045'", self.src)

    def test_same_task_with_new_event_id_is_deduped(self):
        self.assertIn("(taskKey && remembered(KEY_SENT_TASKS, taskKey))", self.src)
        self.assertIn("const alreadyDelivered =", self.src)
        self.assertIn("if (alreadyDelivered)", self.src)

    def test_task_is_remembered_before_dedupe_ack(self):
        block_start = self.src.index("if (alreadyDelivered)")
        block_end = self.src.index("status(ok ? `dedupe ACK", block_start)
        block = self.src[block_start:block_end]
        self.assertLess(
            block.index("remember(KEY_SENT_TASKS, taskKey)"),
            block.index("await ack(event.event_id"),
        )

    def test_task_is_remembered_before_normal_ack(self):
        marker = "const sent = await submitMessage(String(event.message));"
        block_start = self.src.index(marker, self.src.index("wake_new ="))
        block = self.src[block_start:]
        self.assertLess(
            block.index("remember(KEY_SENT_TASKS, taskKey)"),
            block.index("const ok = await ack(event.event_id"),
        )

    def test_recovery_path_uses_result_ready_anchor_and_task_memory(self):
        self.assertIn("RESULT_READY:", self.src)
        self.assertIn("recentUserTurnContainsDelivery(String(event.message))", self.src)
        self.assertIn("const recovered = await ack(event.event_id", self.src)

    def test_v046_patch_preserves_task_dedupe_by_not_removing_key(self):
        patch46 = PATCH.with_name("patch_v046_delivery_guard.py").read_text(encoding="utf-8")
        self.assertNotIn("KEY_SENT_TASKS =", patch46)
        self.assertIn("remember(KEY_SENT_TASKS, taskKey)", patch46)
        self.assertIn("taskKey || String(event.event_id)", patch46)


if __name__ == "__main__":
    unittest.main()
