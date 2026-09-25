#!/usr/bin/env python3
"""Static regression checks for the locally advanced v0.4.6 bridge userscript.

This test is intentionally synced without syncing prediction-chat-wake.user.js,
so the local advanced userscript is inspected in place and is never overwritten
by the stale canonical copy on GitHub.
"""
from pathlib import Path
import unittest

SCRIPT = Path(__file__).with_name("prediction-chat-wake.user.js")


class UserscriptV046GuardStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = SCRIPT.read_text(encoding="utf-8")

    def test_advanced_version_and_task_memory_exist(self):
        self.assertIn("// @version      0.4.6", self.src)
        self.assertIn("const SCRIPT_VERSION = '0.4.6';", self.src)
        self.assertIn("const KEY_SENT_TASKS = 'prediction_sent_tasks_v045';", self.src)

    def test_page_anchor_and_recent_turn_fallback_exist(self):
        self.assertIn("function pageContainsDelivery(text)", self.src)
        self.assertIn("function recentUserTurnContainsDelivery(text, limit = 20)", self.src)
        self.assertIn("return pageContainsDelivery(text);", self.src)

    def test_nonempty_composer_is_never_overwritten(self):
        self.assertIn("const existingComposerText = normalizedChatText(rawComposerText(composer));", self.src)
        self.assertIn("if (existingComposerText) { status('composer niet leeg; bridge wacht', true); return false; }", self.src)

    def test_task_level_dedupe_precedes_submission(self):
        already = self.src.find("const alreadyDelivered =")
        submit = self.src.find("const sent = await submitMessage(String(event.message));", already)
        self.assertGreaterEqual(already, 0)
        self.assertGreater(submit, already)
        block = self.src[already:submit]
        self.assertIn("remembered(KEY_SENT_TASKS, taskKey)", block)
        self.assertIn("recentUserTurnContainsDelivery(String(event.message))", block)
        self.assertIn("if (alreadyDelivered)", block)

    def test_retry_storm_guard_exists(self):
        self.assertIn("const deliveryRetryAfter = new Map();", self.src)
        self.assertIn("deliveryRetryAfter.set(retryKey, Date.now() + 60000);", self.src)
        self.assertIn("if (Date.now() < retryAt)", self.src)

    def test_confirmed_delivery_remembers_task_before_ack(self):
        remember = self.src.find("if (taskKey) remember(KEY_SENT_TASKS, taskKey);")
        ack = self.src.find("const ok = await ack(event.event_id, identity.chatId, identity.consumerId);", remember)
        self.assertGreaterEqual(remember, 0)
        self.assertGreater(ack, remember)


if __name__ == "__main__":
    unittest.main()
