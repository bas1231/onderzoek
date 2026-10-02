from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "control" / "bridge_commands" / "command_bus_poller.py"

spec = importlib.util.spec_from_file_location("command_bus_poller_test", MODULE_PATH)
poller = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(poller)


class CommandBusContinuationTests(unittest.TestCase):
    def base_command(self, **extra):
        obj = {
            "schema": "PREDICTION_BRIDGE_COMMAND_V1",
            "task_id": "DEV-PRED-CONT-NEXT-0123456789abcdef01234567",
            "action": "SIX_AI_HEALTH",
            "created_at_utc": "2026-10-02T18:00:00Z",
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
            "intelligence_tier": "A",
            "issuer": {
                "model": "GPT-5.6 Sol",
                "reasoning_level": "UNAVAILABLE_TO_RUNTIME",
            },
            **extra,
        }
        return obj

    def test_lineage_fields_validate(self):
        ok, reason = poller.validate_command(
            self.base_command(
                auto_continue=True,
                parent_continuation_id="CONT-0123456789abcdef01234567",
                route_task_id="SOURCE-A",
            )
        )
        self.assertTrue(ok, reason)

    def test_bad_parent_continuation_rejected(self):
        ok, reason = poller.validate_command(
            self.base_command(
                parent_continuation_id="CONT-not-a-valid-digest",
            )
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "BAD_PARENT_CONTINUATION_ID")

    def test_headless_auto_continue_rejected(self):
        ok, reason = poller.validate_command(
            self.base_command(
                delivery_mode="headless",
                auto_continue=True,
            )
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "HEADLESS_AUTO_CONTINUE_FORBIDDEN")

    def test_claim_persists_lineage_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old_task_state = poller.TASK_STATE
            old_incidents = poller.INCIDENTS
            poller.TASK_STATE = root / "tasks"
            poller.INCIDENTS = root / "incidents"
            poller.TASK_STATE.mkdir()
            poller.INCIDENTS.mkdir()
            try:
                command = self.base_command(
                    auto_continue=True,
                    parent_continuation_id="CONT-0123456789abcdef01234567",
                    route_task_id="SOURCE-A",
                )
                raw = (json.dumps(command) + "\n").encode("utf-8")

                with patch.object(poller, "remote_bytes", return_value=raw), \
                     patch.object(
                         poller,
                         "resolve_route",
                         return_value=(
                             {
                                 "chat_id": "chat-c-test-24",
                                 "consumer_id": None,
                             },
                             "task:SOURCE-A",
                         ),
                     ), \
                     patch.object(
                         poller,
                         "dispatch",
                         return_value=(
                             "RESPONSE",
                             200,
                             '{"ok":true}',
                         ),
                     ):
                    outcome = poller.process_one(
                        "control/bridge_commands/inbox/test.json",
                        "a" * 40,
                        "token",
                    )

                self.assertEqual(outcome, "DISPATCHED")
                state = json.loads(
                    (
                        poller.TASK_STATE
                        / f"{command['task_id']}.json"
                    ).read_text(encoding="utf-8")
                )
                self.assertIs(state["auto_continue"], True)
                self.assertEqual(
                    state["parent_continuation_id"],
                    "CONT-0123456789abcdef01234567",
                )
            finally:
                poller.TASK_STATE = old_task_state
                poller.INCIDENTS = old_incidents


if __name__ == "__main__":
    unittest.main()
