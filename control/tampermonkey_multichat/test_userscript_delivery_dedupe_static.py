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
        start = self.src.index("const alreadyDelivered =")
        submit = self.src.index("const sent = await submitMessage(message);", start)
        block = self.src[start:submit]
        self.assertIn("remembered(KEY_SENT_EVENTS, eventKey)", block)
        self.assertIn("remembered(KEY_SENT_TASKS, taskKey)", block)
        self.assertIn("recentUserTurnContainsDelivery(message)", block)

    def test_new_event_is_remembered_before_ack(self):
        start = self.src.index("const sent = await submitMessage(message);")
        end = self.src.index("} catch (_)", start)
        body = self.src[start:end]
        remember_event = body.index("remember(KEY_SENT_EVENTS, eventKey);")
        remember_task = body.index("remember(KEY_SENT_TASKS, taskKey);")
        ack_pos = body.index("const ok = await ack(event.event_id, identity.chatId, identity.consumerId);")
        self.assertLess(remember_event, ack_pos)
        self.assertLess(remember_task, ack_pos)

    def test_confirmed_delivery_is_acked_before_generation_exit(self):
        start = self.src.index("const sent = await submitMessage(message);")
        end = self.src.index("} catch (_)", start)
        body = self.src[start:end]
        remember_pos = body.index("remember(KEY_SENT_EVENTS, eventKey);")
        ack_pos = body.index("const ok = await ack(event.event_id, identity.chatId, identity.consumerId);")
        generation_exit_pos = body.rindex("if (generation !== wakeGeneration) return;")
        self.assertGreater(remember_pos, 0)
        self.assertGreater(ack_pos, remember_pos)
        self.assertGreater(generation_exit_pos, ack_pos)
        self.assertNotIn(
            "if (generation !== wakeGeneration) return;\n          if (!sent",
            body,
        )

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
