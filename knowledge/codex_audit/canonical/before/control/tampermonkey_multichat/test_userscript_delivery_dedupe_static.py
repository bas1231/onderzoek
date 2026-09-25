#!/usr/bin/env python3
"""Static regression guard for browser-side bridge delivery dedupe.

This intentionally tests the canonical userscript source without executing a browser.
It protects the restart/stale-replay invariant: an event remembered as sent must be
ACKed and skipped, while a newly submitted event must be remembered before ACK.
"""
from pathlib import Path
import re
import unittest

SCRIPT = Path(__file__).with_name("prediction-chat-wake.user.js")


class UserscriptDeliveryDedupeStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = SCRIPT.read_text(encoding="utf-8")

    def test_sent_event_memory_is_persistent_gm_storage(self):
        self.assertRegex(
            self.src,
            r"const KEY_SENT_EVENTS\s*=\s*['\"]prediction_sent_events_v3['\"]",
        )
        self.assertIn("GM_getValue(key, [])", self.src)
        self.assertIn("GM_setValue(key, values)", self.src)

    def test_remembered_event_is_acked_and_not_resubmitted(self):
        pattern = re.compile(
            r"if \(remembered\(KEY_SENT_EVENTS, event\.event_id\)\) \{\s*"
            r"await ack\(event\.event_id, identity\.chatId, identity\.consumerId\);\s*"
            r"continue;\s*\}",
            re.S,
        )
        self.assertRegex(self.src, pattern)

    def test_new_event_is_remembered_before_ack(self):
        remember_at = self.src.find("remember(KEY_SENT_EVENTS, event.event_id);")
        ack_at = self.src.find(
            "const ok = await ack(event.event_id, identity.chatId, identity.consumerId);",
            remember_at,
        )
        self.assertGreaterEqual(remember_at, 0)
        self.assertGreater(ack_at, remember_at)

    def test_restart_does_not_clear_sent_event_memory(self):
        match = re.search(
            r"function restartWakeLoop\(reason\) \{(?P<body>.*?)\n  \}",
            self.src,
            re.S,
        )
        self.assertIsNotNone(match)
        body = match.group("body")
        self.assertNotIn("GM_setValue(KEY_SENT_EVENTS", body)
        self.assertNotIn("KEY_SENT_EVENTS, []", body)


if __name__ == "__main__":
    unittest.main()
