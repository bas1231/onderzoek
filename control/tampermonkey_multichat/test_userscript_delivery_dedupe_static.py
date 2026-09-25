#!/usr/bin/env python3
"""Static regression guard for browser-side bridge delivery dedupe.

This intentionally tests the canonical userscript source without executing a browser.
It protects the restart/stale-replay invariant: an event remembered as sent must be
ACKed and skipped, while a newly submitted event must be remembered before ACK.
"""
from pathlib import Path
import re
import runpy
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
        behavior = runpy.run_path(str(SCRIPT.parents[2] / 'tests/audit/test_delivery_behavior.py'))
        behavior['test_event_memory_survives_new_script_instance']()

    def test_new_event_is_remembered_before_ack(self):
        behavior = runpy.run_path(str(SCRIPT.parents[2] / 'tests/audit/test_delivery_behavior.py'))
        behavior['test_new_event_receipt_written_before_ack']()

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
