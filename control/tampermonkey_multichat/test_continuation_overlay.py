from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[2] / "control" / "tampermonkey_multichat"
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import bridge_server_continuation as bridge
import continuation_manager as cm


class ContinuationOverlayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)

        bridge.base.DATA_DIR = root / "bridge"
        bridge.base.OUTBOX = bridge.base.DATA_DIR / "outbox"
        bridge.base.INFLIGHT = bridge.base.DATA_DIR / "inflight"
        bridge.base.SENT = bridge.base.DATA_DIR / "sent"
        bridge.base.ROUTES = bridge.base.DATA_DIR / "routes"

        for p in (
            bridge.base.OUTBOX,
            bridge.base.INFLIGHT,
            bridge.base.SENT,
            bridge.base.ROUTES,
            cm.continuation_dir(bridge.base.DATA_DIR),
        ):
            p.mkdir(parents=True, exist_ok=True)

        bridge.TASK_STATE_DIR = root / "tasks"
        bridge.TASK_STATE_DIR.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def write_task_state(self, task_id: str, **extra):
        obj = {
            "schema": "PREDICTION_COMMAND_BUS_TASK_STATE_V1",
            "task_id": task_id,
            "status": "DISPATCHED",
            **extra,
        }
        (bridge.TASK_STATE_DIR / f"{task_id}.json").write_text(
            json.dumps(obj),
            encoding="utf-8",
        )

    def test_source_result_ack_starts_one_continuation(self):
        self.write_task_state("SOURCE-A", auto_continue=True)
        event = {
            "event_id": "result-a",
            "task_id": "SOURCE-A",
            "message": "PASS",
        }

        bridge.continuation_ack_hook(
            event,
            chat_id="chat-c-test-24",
            consumer_id="ext-tab-a",
            already_acked=False,
        )
        bridge.continuation_ack_hook(
            event,
            chat_id="chat-c-test-24",
            consumer_id="ext-tab-a",
            already_acked=True,
        )

        paths = list(
            cm.continuation_dir(
                bridge.base.DATA_DIR
            ).glob("CONT-*.json")
        )
        self.assertEqual(len(paths), 1)
        record = json.loads(
            paths[0].read_text(encoding="utf-8")
        )
        self.assertEqual(
            record["state"],
            "CONTINUE_REQUESTED",
        )
        self.assertEqual(
            record["source_task_id"],
            "SOURCE-A",
        )

    def test_continuation_delivery_ack_marks_sent_not_terminal(self):
        self.write_task_state("SOURCE-A", auto_continue=True)
        record = cm.start_for_result_ack(
            data_dir=bridge.base.DATA_DIR,
            task_state_dir=bridge.TASK_STATE_DIR,
            source_task_id="SOURCE-A",
            chat_id="chat-c-test-24",
        )
        self.assertIsNotNone(record)

        cm.enqueue_attempt(
            record=record,
            data_dir=bridge.base.DATA_DIR,
            routes_dir=bridge.base.ROUTES,
            outbox_dir=bridge.base.OUTBOX,
            now=1000.0,
        )

        stored = json.loads(
            cm.continuation_path(
                bridge.base.DATA_DIR,
                record["continuation_id"],
            ).read_text(encoding="utf-8")
        )

        event = json.loads(
            (
                bridge.base.OUTBOX
                / f"{stored['last_event_id']}.json"
            ).read_text(encoding="utf-8")
        )

        bridge.continuation_ack_hook(
            event,
            chat_id="chat-c-test-24",
            consumer_id="ext-tab-a",
            already_acked=False,
        )

        final = json.loads(
            cm.continuation_path(
                bridge.base.DATA_DIR,
                record["continuation_id"],
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            final["state"],
            "CONTINUE_SENT",
        )
        self.assertNotIn(
            final["state"],
            cm.TERMINAL_STATES,
        )
        self.assertEqual(
            len(
                list(
                    cm.continuation_dir(
                        bridge.base.DATA_DIR
                    ).glob("CONT-*.json")
                )
            ),
            1,
        )

    def test_overlay_installs_explicit_ack_hook(self):
        self.assertIs(
            bridge.base.ACK_HOOK,
            bridge.continuation_ack_hook,
        )


if __name__ == "__main__":
    unittest.main()
