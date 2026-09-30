from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import bridge_server_route_resilience as mod


class RouteConsumerResilienceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.saved = {
            "DATA_DIR": mod.base.DATA_DIR,
            "OUTBOX": mod.base.OUTBOX,
            "SENT": mod.base.SENT,
            "ROUTES": mod.base.ROUTES,
            "DEFAULT_CHAT_FILE": mod.base.DEFAULT_CHAT_FILE,
        }
        if hasattr(mod.base, "INFLIGHT"):
            self.saved["INFLIGHT"] = mod.base.INFLIGHT
        mod.base.DATA_DIR = root
        mod.base.OUTBOX = root / "outbox"
        mod.base.SENT = root / "sent"
        mod.base.ROUTES = root / "routes"
        mod.base.DEFAULT_CHAT_FILE = root / "default_chat.json"
        if hasattr(mod.base, "INFLIGHT"):
            mod.base.INFLIGHT = root / "inflight"
        for p in (mod.base.OUTBOX, mod.base.SENT, mod.base.ROUTES):
            p.mkdir(parents=True, exist_ok=True)
        if hasattr(mod.base, "INFLIGHT"):
            mod.base.INFLIGHT.mkdir(parents=True, exist_ok=True)
        mod.base.LEASES.clear()

    def tearDown(self):
        mod.base.LEASES.clear()
        for key, value in self.saved.items():
            setattr(mod.base, key, value)
        self.tmp.cleanup()

    def _write_route_and_event(self):
        task = "TEST-STALE-CONSUMER-E001"
        chat = "chat-c-resilience-01"
        old_consumer = "tab-old-consumer-01"
        (mod.base.ROUTES / f"{task}.json").write_text(json.dumps({
            "version": 2,
            "task_id": task,
            "chat_id": chat,
            "consumer_id": old_consumer,
        }), encoding="utf-8")
        (mod.base.OUTBOX / "event-resilience.json").write_text(json.dumps({
            "event_id": "event-resilience",
            "task_id": task,
            "message": "BRIDGE_RESULT: BRIDGE_PONG",
        }), encoding="utf-8")
        return task, chat, old_consumer

    def test_stored_consumer_is_normalized_to_chat_scope(self):
        task, chat, _ = self._write_route_and_event()
        binding = mod.base.route_binding_for_task(task)
        self.assertEqual(binding, {"chat_id": chat, "consumer_id": None})

    def test_same_chat_new_consumer_can_lease_old_route(self):
        _, chat, _ = self._write_route_and_event()
        raw_oldest = mod.session.hardened._RAW_OLDEST_EVENT
        path, obj = raw_oldest(chat, "tab-new-consumer-02")
        self.assertIsNotNone(path)
        self.assertEqual(obj["event_id"], "event-resilience")

    def test_other_chat_still_cannot_lease_event(self):
        self._write_route_and_event()
        raw_oldest = mod.session.hardened._RAW_OLDEST_EVENT
        path, obj = raw_oldest("chat-c-other-02", "tab-other-consumer-02")
        self.assertIsNone(path)
        self.assertIsNone(obj)

    def test_compactor_preserves_bridge_ping_pass_and_nested_outer_pass(self):
        ping = mod.compact_delivery_event({
            "event_id": "ping-1",
            "task_id": "PING-E001",
            "message": "RESULT_READY: PING-E001\nExit code: 0\nBRIDGE_RESULT: BRIDGE_PONG",
        })["message"]
        self.assertIn("status=PASS", ping)
        self.assertIn("exit=0", ping)

        nested = mod.compact_delivery_event({
            "event_id": "nested-1",
            "task_id": "OUTER-E001",
            "message": "\n".join([
                "RESULT_READY: OUTER-E001",
                "Exit code: 0",
                "DEV_TASK_STATUS=FAIL",
                "ERROR_CLASS=TaskError",
                "COMMAND_1_RC=2",
                "COMMAND_1_RC=0",
                "DEV_TASK_STATUS=PASS",
            ]),
        })["message"]
        self.assertIn("status=PASS", nested)
        self.assertIn("rcs=1:0", nested)
        self.assertNotIn("error=", nested)


if __name__ == "__main__":
    unittest.main()
