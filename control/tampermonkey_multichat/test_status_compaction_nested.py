from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import bridge_server_status_compaction as mod


class NestedStatusCompactionTests(unittest.TestCase):
    def compact(self, raw: str) -> str:
        obj = {
            "event_id": "event-test-1",
            "task_id": "DEV-OUTER-E001",
            "message": raw,
        }
        return mod.compact_delivery_event(obj)["message"]

    def test_nested_old_failure_does_not_flip_outer_pass(self):
        raw = "\n".join([
            "RESULT_READY: DEV-OUTER-E001",
            "Action: SIX_AI_HEALTH",
            "Exit code: 0",
            "=== WSL RESULT ===",
            "DEV_TASK_ID=DEV-OUTER-E001",
            "COMMAND_1_BEGIN=python3",
            "--- RECEIPT_TAIL ---",
            "DEV_TASK_ID=DEV-OLD-E009",
            "COMMAND_1_RC=2",
            "DEV_TASK_STATUS=FAIL",
            "ERROR_CLASS=TaskError",
            "ERROR=old nested failure detail",
            "--- END_RECEIPT_TAIL ---",
            "DIAG=PASS",
            "COMMAND_1_RC=0",
            "COMMAND_1_END=1",
            "DEV_TASK_STATUS=PASS",
        ])
        message = self.compact(raw)
        self.assertIn("status=PASS", message)
        self.assertIn("exit=0", message)
        self.assertIn("rcs=1:0", message)
        self.assertNotIn("error=", message)
        self.assertNotIn("detail=", message)
        self.assertNotIn("1:2", message)

    def test_outer_fail_wins_over_nested_pass_and_surfaces_detail(self):
        raw = "\n".join([
            "RESULT_READY: DEV-OUTER-E001",
            "Exit code: 2",
            "=== WSL RESULT ===",
            "DEV_TASK_ID=DEV-OUTER-E001",
            "COMMAND_1_BEGIN=python3",
            "DEV_TASK_ID=DEV-INNER-E001",
            "COMMAND_1_RC=0",
            "DEV_TASK_STATUS=PASS",
            "COMMAND_1_RC=2",
            "ERROR_CLASS=TaskError",
            "ERROR=python rc=1: BUILD_PLANNER_PIN_NOT_UPDATED",
            "DEV_TASK_STATUS=FAIL",
        ])
        message = self.compact(raw)
        self.assertIn("status=FAIL", message)
        self.assertIn("exit=2", message)
        self.assertIn("rcs=1:2", message)
        self.assertIn("error=TaskError", message)
        self.assertIn("detail=python rc=1: BUILD_PLANNER_PIN_NOT_UPDATED", message)

    def test_non_wsl_message_is_unchanged(self):
        message = self.compact("ordinary bridge message")
        self.assertEqual(message, "ordinary bridge message")


if __name__ == "__main__":
    unittest.main()
