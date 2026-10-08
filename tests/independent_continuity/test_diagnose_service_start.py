"""Pure regression tests for the sidecar startup journal diagnostic."""
from __future__ import annotations

import unittest

from control.independent_continuity.diagnose_service_start import describe_journal


class StartupDiagnosisTests(unittest.TestCase):
    def test_runner_fail_closed_reason(self):
        journal = 'systemd: Started service\n{"status":"FAIL_CLOSED","reason":"source snapshot stale"}\nservice failed'
        self.assertEqual(describe_journal(journal), ("OBSERVER_FAIL_CLOSED", "source snapshot stale"))

    def test_syntax_traceback_is_visible_as_error(self):
        kind, msg = describe_journal("Traceback (most recent call last):\nModuleNotFoundError: No module named observer")
        self.assertEqual(kind, "OBSERVER_JOURNAL_ERROR")
        self.assertIn("ModuleNotFoundError", msg)

    def test_invalid_observer_input(self):
        kind, msg = describe_journal('{"status":"INPUT_INVALID","errors":["Bad event E012"]}')
        self.assertEqual((kind, msg), ("OBSERVER_INPUT_INVALID", "Bad event E012"))

    def test_no_cause_is_not_assumed_healthy(self):
        kind, _ = describe_journal("Started oneshot service")
        self.assertEqual(kind, "OBSERVER_CAUSE_UNCLASSIFIED")


if __name__ == "__main__":
    unittest.main()
