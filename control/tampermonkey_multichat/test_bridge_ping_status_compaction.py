from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import bridge_server_status_compaction_v11 as mod


class BridgePingStatusCompactionTests(unittest.TestCase):
    def compact(self, raw: str) -> str:
        return mod.compact_delivery_event({
            "event_id": "event-bridge-ping-status",
            "task_id": "BRIDGE-PING-TEST-E001",
            "message": raw,
        })["message"]

    def test_bridge_pong_exit_zero_is_pass(self):
        raw = "\n".join([
            "RESULT_READY: BRIDGE-PING-TEST-E001",
            "Action: BRIDGE_PING",
            "Exit code: 0",
            "=== WSL RESULT ===",
            "BRIDGE_PONG",
        ])
        message = self.compact(raw)
        self.assertIn("status=PASS", message)
        self.assertIn("exit=0", message)

    def test_bridge_pong_nonzero_is_fail(self):
        raw = "\n".join([
            "RESULT_READY: BRIDGE-PING-TEST-E001",
            "Action: BRIDGE_PING",
            "Exit code: 7",
            "=== WSL RESULT ===",
            "BRIDGE_PONG",
        ])
        message = self.compact(raw)
        self.assertIn("status=FAIL", message)
        self.assertIn("exit=7", message)

    def test_non_dev_exit_zero_without_bridge_pong_stays_unknown(self):
        raw = "\n".join([
            "RESULT_READY: OTHER-E001",
            "Exit code: 0",
            "=== WSL RESULT ===",
            "OTHER_OUTPUT",
        ])
        self.assertIn("status=UNKNOWN", self.compact(raw))

    def test_nested_dev_status_rules_are_preserved(self):
        raw = "\n".join([
            "RESULT_READY: DEV-OUTER-E001",
            "Exit code: 0",
            "=== WSL RESULT ===",
            "DEV_TASK_STATUS=FAIL",
            "ERROR_CLASS=OldFailure",
            "COMMAND_1_RC=2",
            "COMMAND_1_RC=0",
            "DEV_TASK_STATUS=PASS",
        ])
        message = self.compact(raw)
        self.assertIn("status=PASS", message)
        self.assertIn("rcs=1:0", message)
        self.assertNotIn("error=", message)


if __name__ == "__main__":
    unittest.main()
