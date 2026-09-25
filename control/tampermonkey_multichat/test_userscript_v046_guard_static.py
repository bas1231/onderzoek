"""Voormalige v0.4.6 letterlijke checks, nu canonical gedragscontracten.

Geen pin op een historische deploymentversie. Dedupe, userturnbewijs,
conceptbehoud, backoff en durable-before-ACK worden daadwerkelijk uitgevoerd.
"""
from pathlib import Path
import re
import runpy
import unittest

ROOT = Path(__file__).resolve().parents[2]
BEHAVIOR = runpy.run_path(str(ROOT / 'tests/audit/test_delivery_behavior.py'))
RELIABILITY = runpy.run_path(str(ROOT / 'tests/audit/test_reliability_regressions.py'))

class UserscriptV046GuardStaticTests(unittest.TestCase):
    def test_advanced_version_and_task_memory_exist(self):
        src=Path(__file__).with_name('prediction-chat-wake.user.js').read_text()
        metadata=re.search(r'// @version\s+([0-9.]+)',src).group(1)
        runtime=re.search(r"const SCRIPT_VERSION = '([0-9.]+)'",src).group(1)
        self.assertEqual(metadata,runtime)
        self.assertGreaterEqual(tuple(map(int,metadata.split('.'))),(0,4,6))
        BEHAVIOR['test_task_memory_written_before_ack']()

    def test_page_anchor_and_recent_turn_fallback_exist(self):
        BEHAVIOR['test_exact_visible_user_turn_recovers_delivery']()
        BEHAVIOR['test_partial_anchor_is_not_delivery_evidence']()

    def test_nonempty_composer_is_never_overwritten(self):
        for scenario in ['draft','no_button','concurrent_edit','normal']:
            RELIABILITY['test_composer_ownership_and_retry'](scenario)

    def test_task_level_dedupe_precedes_submission(self):
        BEHAVIOR['test_task_replayed_with_new_event_is_not_resubmitted']()
        BEHAVIOR['test_same_task_changed_result_is_not_silently_dropped']()

    def test_retry_storm_guard_exists(self):
        BEHAVIOR['test_retry_backoff_preserves_unacked_event']()

    def test_confirmed_delivery_remembers_task_before_ack(self):
        BEHAVIOR['test_task_memory_written_before_ack']()
        BEHAVIOR['test_ack_failure_keeps_delivery_memory']()
