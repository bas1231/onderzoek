from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import continuation_manager as cm


class ContinuationManagerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.data = self.root / "bridge"
        self.tasks = self.root / "tasks"
        self.outbox = self.data / "outbox"
        self.inflight = self.data / "inflight"
        self.sent = self.data / "sent"
        self.routes = self.data / "routes"
        for p in (
            self.tasks,
            self.outbox,
            self.inflight,
            self.sent,
            self.routes,
            cm.continuation_dir(self.data),
        ):
            p.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def write_state(self, task_id: str, **extra):
        obj = {
            "schema": "PREDICTION_COMMAND_BUS_TASK_STATE_V1",
            "task_id": task_id,
            "status": "DISPATCHED",
            **extra,
        }
        (self.tasks / f"{task_id}.json").write_text(
            json.dumps(obj), encoding="utf-8"
        )
        return obj

    def start(self, source="SOURCE-A"):
        self.write_state(source, auto_continue=True)
        record = cm.start_for_result_ack(
            data_dir=self.data,
            task_state_dir=self.tasks,
            source_task_id=source,
            chat_id="chat-c-test-24",
        )
        self.assertIsNotNone(record)
        return record

    def load_record(self, record):
        return json.loads(
            cm.continuation_path(
                self.data, record["continuation_id"]
            ).read_text(encoding="utf-8")
        )

    def test_full_source_id_hash_prevents_truncation_collision(self):
        prefix = "X" * 140
        a = cm.ids_for(prefix + "-A")
        b = cm.ids_for(prefix + "-B")
        self.assertNotEqual(a["continuation_id"], b["continuation_id"])

    def test_source_without_auto_continue_is_ignored(self):
        self.write_state("SOURCE-NO", auto_continue=False)
        self.assertIsNone(
            cm.start_for_result_ack(
                data_dir=self.data,
                task_state_dir=self.tasks,
                source_task_id="SOURCE-NO",
                chat_id="chat-c-test-24",
            )
        )

    def test_start_is_idempotent(self):
        first = self.start()
        second = cm.start_for_result_ack(
            data_dir=self.data,
            task_state_dir=self.tasks,
            source_task_id="SOURCE-A",
            chat_id="chat-c-test-24",
        )
        self.assertEqual(first["continuation_id"], second["continuation_id"])
        self.assertEqual(
            len(list(cm.continuation_dir(self.data).glob("*.json"))), 1
        )

    def test_pending_delivery_is_not_reoffered(self):
        record = self.start()
        self.assertTrue(
            cm.enqueue_attempt(
                record=record,
                data_dir=self.data,
                routes_dir=self.routes,
                outbox_dir=self.outbox,
                now=1000.0,
            )
        )
        stored = self.load_record(record)
        self.assertEqual(stored["state"], "CONTINUE_QUEUED")
        self.assertFalse(
            cm.enqueue_attempt(
                record=stored,
                data_dir=self.data,
                routes_dir=self.routes,
                outbox_dir=self.outbox,
                now=9999.0,
            )
        )
        self.assertEqual(len(list(self.outbox.glob("*.json"))), 1)

    def test_browser_ack_is_nonterminal_and_retry_gets_new_delivery_id(self):
        record = self.start()
        with patch.object(cm.time, "time", return_value=1000.0):
            self.assertTrue(
                cm.enqueue_attempt(
                    record=record,
                    data_dir=self.data,
                    routes_dir=self.routes,
                    outbox_dir=self.outbox,
                    now=1000.0,
                )
            )
        queued = self.load_record(record)
        event_path = self.outbox / f"{queued['last_event_id']}.json"
        event = json.loads(event_path.read_text(encoding="utf-8"))
        event_path.rename(self.sent / event_path.name)

        with patch.object(cm.time, "time", return_value=1001.0):
            self.assertTrue(
                cm.mark_delivery_acked(data_dir=self.data, event=event)
            )
        acked = self.load_record(record)
        self.assertEqual(acked["state"], "CONTINUE_SENT")
        self.assertNotIn(acked["state"], cm.TERMINAL_STATES)

        self.assertFalse(
            cm.enqueue_attempt(
                record=acked,
                data_dir=self.data,
                routes_dir=self.routes,
                outbox_dir=self.outbox,
                now=1001.0 + cm.RETRY_AFTER_SECONDS - 1,
            )
        )
        self.assertTrue(
            cm.enqueue_attempt(
                record=acked,
                data_dir=self.data,
                routes_dir=self.routes,
                outbox_dir=self.outbox,
                now=1001.0 + cm.RETRY_AFTER_SECONDS + 1,
            )
        )
        retried = self.load_record(record)
        self.assertEqual(retried["attempts"], 2)
        self.assertTrue(retried["last_attempt_task_id"].endswith("-A02"))
        self.assertNotEqual(
            retried["last_event_id"], queued["last_event_id"]
        )

    def test_duplicate_browser_ack_is_idempotent(self):
        record = self.start()
        cm.enqueue_attempt(
            record=record,
            data_dir=self.data,
            routes_dir=self.routes,
            outbox_dir=self.outbox,
            now=1000.0,
        )
        stored = self.load_record(record)
        event = json.loads(
            (self.outbox / f"{stored['last_event_id']}.json").read_text(
                encoding="utf-8"
            )
        )
        with patch.object(cm.time, "time", return_value=1001.0):
            self.assertTrue(cm.mark_delivery_acked(data_dir=self.data, event=event))
            self.assertTrue(cm.mark_delivery_acked(data_dir=self.data, event=event))
        final = self.load_record(record)
        sent_states = [
            h for h in final["history"] if h["state"] == "CONTINUE_SENT"
        ]
        self.assertEqual(len(sent_states), 1)

    def test_next_dispatched_is_terminal(self):
        record = self.start()
        self.write_state(
            record["expected_next_task_id"],
            status="DISPATCHED",
            parent_continuation_id=record["continuation_id"],
        )
        self.assertTrue(cm.reconcile(record, self.tasks))
        self.assertEqual(record["state"], "NEXT_TASK_ACCEPTED")

    def test_done_dispatched_is_terminal(self):
        record = self.start()
        self.write_state(
            record["expected_done_task_id"],
            status="DISPATCHED",
            parent_continuation_id=record["continuation_id"],
        )
        self.assertTrue(cm.reconcile(record, self.tasks))
        self.assertEqual(record["state"], "DONE")

    def test_multiple_outcomes_fail_closed(self):
        record = self.start()
        self.write_state(record["expected_next_task_id"], status="DISPATCHED")
        self.write_state(record["expected_done_task_id"], status="DISPATCHED")
        self.assertTrue(cm.reconcile(record, self.tasks))
        self.assertEqual(record["state"], "CONFLICT")

    def test_stale_claimed_child_blocks(self):
        record = self.start()
        self.write_state(
            record["expected_next_task_id"],
            status="CLAIMED",
            claimed_at_utc="2026-01-01T00:00:00Z",
        )
        self.assertTrue(cm.reconcile(record, self.tasks, now=2_000_000_000.0))
        self.assertEqual(record["state"], "BLOCKED")

    def test_bounded_retry_exhaustion_blocks_transport(self):
        record = self.start()
        record["attempts"] = cm.MAX_ATTEMPTS
        record["last_attempt_at"] = 0.0
        cm._atomic_json(
            cm.continuation_path(self.data, record["continuation_id"]),
            record,
        )
        self.assertFalse(
            cm.enqueue_attempt(
                record=record,
                data_dir=self.data,
                routes_dir=self.routes,
                outbox_dir=self.outbox,
                now=9999.0,
            )
        )
        self.assertEqual(self.load_record(record)["state"], "BLOCKED_TRANSPORT")


if __name__ == "__main__":
    unittest.main()
