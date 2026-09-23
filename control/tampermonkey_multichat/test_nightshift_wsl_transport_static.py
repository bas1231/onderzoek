#!/usr/bin/env python3
"""Static regression guard for the dedicated nightshift WSL transport.

Protects the invariants that matter after the earlier RESULT_READY dump loop:
- only the dedicated allowlisted nightshift task namespace is accepted;
- localhost traffic uses Tampermonkey GM_xmlhttpRequest with @connect localhost;
- WSL results are compacted into a short summary instead of posting raw output;
- the summary has a hard character cap;
- result events are ACKed through the existing bridge API;
- wake text remains independent from WSL result delivery.
"""
from pathlib import Path
import re
import unittest

SCRIPT = Path(__file__).with_name("prediction-nightshift-wake.user.js")


class NightshiftWslTransportStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = SCRIPT.read_text(encoding="utf-8")

    def test_tampermonkey_localhost_transport_is_declared(self):
        self.assertIn("// @grant        GM_xmlhttpRequest", self.src)
        self.assertIn("// @connect      localhost", self.src)
        self.assertIn("http://localhost:8767", self.src)
        self.assertIn("http://localhost:8765", self.src)

    def test_command_scope_is_nightshift_only(self):
        self.assertIn("const ALLOWED_ACTION = 'SIX_AI_HEALTH';", self.src)
        self.assertIn("const TASK_PREFIX = 'DEV-PRED-NIGHTSHIFT-';", self.src)
        self.assertRegex(
            self.src,
            r"PREDICTION_CMD:\(SIX_AI_HEALTH\).*DEV-PRED-NIGHTSHIFT-",
        )

    def test_result_is_compacted_and_hard_capped(self):
        self.assertIn("function compactResult(event)", self.src)
        self.assertIn("const MAX_SUMMARY_CHARS = 900;", self.src)
        self.assertIn(".slice(0, MAX_SUMMARY_CHARS)", self.src)
        self.assertNotIn("submitText(String(event.message", self.src)
        self.assertNotIn("fillComposer(composer, String(event.message", self.src)

    def test_compact_result_reports_status_not_raw_stdout(self):
        self.assertIn("DEV_TASK_STATUS=(PASS|FAIL)", self.src)
        self.assertIn("COMMAND_(\\d+)_RC=(-?\\d+)", self.src)
        self.assertIn("NIGHTSHIFT_WSL_RESULT_V1", self.src)

    def test_event_is_acked_via_existing_bridge(self):
        self.assertIn("url: `${WAKE_BASE}/ack`", self.src)
        self.assertIn("await ackEvent(pending.eventId, identity)", self.src)

    def test_wake_text_stays_simple_and_separate(self):
        self.assertIn("const WAKE_TEXT = 'ga door';", self.src)
        self.assertNotIn("RESULT_READY", re.search(
            r"const WAKE_TEXT\s*=\s*([^;]+);", self.src
        ).group(1))


if __name__ == "__main__":
    unittest.main()
