from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import bridge_server_session_bootstrap as mod


class SessionBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        mod.base.DATA_DIR = root
        mod.base.OUTBOX = root / "outbox"
        mod.base.SENT = root / "sent"
        mod.base.ROUTES = root / "routes"
        mod.base.INFLIGHT = root / "inflight"
        mod.base.DEFAULT_CHAT_FILE = root / "default_chat.json"
        for p in (mod.base.OUTBOX, mod.base.SENT, mod.base.ROUTES, mod.base.INFLIGHT):
            p.mkdir(parents=True, exist_ok=True)
        mod.hardened.base = mod.base

    def tearDown(self):
        self.tmp.cleanup()

    def _event_for(self, directory: Path, task_id: str):
        for path in directory.glob("*.json"):
            obj = json.loads(path.read_text(encoding="utf-8"))
            if obj.get("task_id") == task_id:
                return path, obj
        return None, None

    def test_new_chat_gets_chat_scoped_route_and_pass_announcement(self):
        chat = "chat-c-deadbeef-24"
        consumer = "tab-abcdef123456"
        task = mod.ensure_session_bootstrap(chat, consumer)
        self.assertTrue(task.startswith("SESSION-ROUTE-"))
        route = json.loads((mod.base.ROUTES / f"{task}.json").read_text(encoding="utf-8"))
        self.assertEqual(route["chat_id"], chat)
        self.assertIsNone(route["consumer_id"])
        _, event = self._event_for(mod.base.OUTBOX, task)
        self.assertIsNotNone(event)
        self.assertIn(f"task={task}", event["message"])
        self.assertIn("status=PASS exit=0", event["message"])
        self.assertIn("kind=SESSION_ROUTE_BOOTSTRAP", event["message"])

    def test_sent_routed_result_suppresses_bootstrap(self):
        chat = "chat-c-aabbccdd-24"
        old_task = "EXISTING-PROVEN-ROUTE-E001"
        (mod.base.ROUTES / f"{old_task}.json").write_text(json.dumps({
            "version": 2, "task_id": old_task, "chat_id": chat, "consumer_id": None
        }), encoding="utf-8")
        (mod.base.SENT / "existing.json").write_text(json.dumps({
            "event_id": "existing", "task_id": old_task, "message": "PASS"
        }), encoding="utf-8")
        self.assertIsNone(mod.ensure_session_bootstrap(chat, "tab-12345678"))
        self.assertFalse(any(p.name.startswith("SESSION-ROUTE-") for p in mod.base.ROUTES.glob("*.json")))

    def test_duplicate_outbox_is_not_created(self):
        chat = "chat-c-11223344-24"
        consumer = "tab-12345678"
        task = mod.ensure_session_bootstrap(chat, consumer)
        first = list(mod.base.OUTBOX.glob("*.json"))
        self.assertEqual(len(first), 1)
        task2 = mod.ensure_session_bootstrap(chat, consumer)
        self.assertEqual(task2, task)
        self.assertEqual(len(list(mod.base.OUTBOX.glob("*.json"))), 1)

    def test_stale_inflight_bootstrap_is_safely_reannounced(self):
        chat = "chat-c-55667788-24"
        consumer = "tab-87654321"
        task = mod.ensure_session_bootstrap(chat, consumer)
        path, _ = self._event_for(mod.base.OUTBOX, task)
        self.assertIsNotNone(path)
        inflight = mod.base.INFLIGHT / path.name
        os.replace(path, inflight)
        old = time.time() - (mod.REANNOUNCE_AFTER_SECONDS + 10)
        os.utime(inflight, (old, old))
        mod.ensure_session_bootstrap(chat, consumer)
        self.assertEqual(len(list(mod.base.OUTBOX.glob("*.json"))), 1)
        _, event = self._event_for(mod.base.OUTBOX, task)
        self.assertEqual(event["task_id"], task)

    def test_same_chat_route_is_stable_across_consumers(self):
        chat = "chat-c-cafebabe-24"
        a = mod._session_task_id(chat)
        b = mod._session_task_id(chat)
        self.assertEqual(a, b)
        self.assertEqual(a, mod.ensure_session_bootstrap(chat, "tab-first123"))
        self.assertEqual(a, mod.ensure_session_bootstrap(chat, "tab-second456"))


if __name__ == "__main__":
    unittest.main()
