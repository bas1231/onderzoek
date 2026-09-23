#!/usr/bin/env python3
"""Regression tests for bridge_server_v2 delivery semantics.

These tests are intentionally standard-library only so they can run on the
local WSL checkout without extra dependencies.

Covers the failure mode seen on 2026-09-23: an already-ACKed RESULT_READY must
never become eligible for /next again, and repeated ACK must be idempotent.
"""

from __future__ import annotations

import importlib.util
import json
import threading
import tempfile
import unittest
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "bridge_server_v2.py"


def load_bridge_module():
    spec = importlib.util.spec_from_file_location("bridge_server_v2_under_test", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SentOutboxSemanticsTest(unittest.TestCase):
    def setUp(self):
        self.bridge = load_bridge_module()
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.bridge.DATA_DIR = root
        self.bridge.OUTBOX = root / "outbox"
        self.bridge.SENT = root / "sent"
        self.bridge.ROUTES = root / "routes"
        self.bridge.DEFAULT_CHAT_FILE = root / "default_chat.json"
        self.bridge.TOKEN_FILE = root / "token"
        self.bridge.USERSCRIPT_FILE = root / "prediction-chat-wake.user.js"
        self.bridge.LEASES.clear()
        self.bridge.ensure_dirs()
        self.token = "test-token"
        self.chat_id = "chat-test-0001"
        self.consumer_id = "consumer-test-0001"
        self.task_id = "TEST-RESULT-READY-E001"
        self.event_id = "1234567890-deadbeef"

    def tearDown(self):
        self.bridge.LEASES.clear()
        self.tmp.cleanup()

    def write_route(self):
        (self.bridge.ROUTES / f"{self.task_id}.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "task_id": self.task_id,
                    "chat_id": self.chat_id,
                }
            ),
            encoding="utf-8",
        )

    def event(self):
        return {
            "version": 1,
            "event_id": self.event_id,
            "task_id": self.task_id,
            "message": f"RESULT_READY: {self.task_id}",
        }

    def test_sent_event_is_never_eligible_for_oldest_event(self):
        self.write_route()
        (self.bridge.SENT / f"{self.event_id}.json").write_text(
            json.dumps(self.event()), encoding="utf-8"
        )

        path, obj = self.bridge.oldest_event(self.chat_id, self.consumer_id)

        self.assertIsNone(path)
        self.assertIsNone(obj)

    def test_outbox_event_is_eligible_before_ack(self):
        self.write_route()
        outbox_path = self.bridge.OUTBOX / f"{self.event_id}.json"
        outbox_path.write_text(json.dumps(self.event()), encoding="utf-8")

        path, obj = self.bridge.oldest_event(self.chat_id, self.consumer_id)

        self.assertEqual(path, outbox_path)
        self.assertEqual(obj["event_id"], self.event_id)

    def test_repeated_ack_is_idempotent_and_does_not_restore_outbox(self):
        self.write_route()
        outbox_path = self.bridge.OUTBOX / f"{self.event_id}.json"
        sent_path = self.bridge.SENT / f"{self.event_id}.json"
        outbox_path.write_text(json.dumps(self.event()), encoding="utf-8")

        # Lease first, exactly as /next does before the browser ACKs the event.
        path, obj = self.bridge.oldest_event(self.chat_id, self.consumer_id)
        self.assertEqual(path, outbox_path)
        self.assertEqual(obj["event_id"], self.event_id)

        httpd = self.bridge.ThreadingHTTPServer(("127.0.0.1", 0), self.bridge.Handler)
        httpd.daemon_threads = True
        httpd.bridge_token = self.token
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{httpd.server_address[1]}/ack"
            body = json.dumps(
                {
                    "event_id": self.event_id,
                    "chat_id": self.chat_id,
                    "consumer_id": self.consumer_id,
                }
            ).encode("utf-8")

            def post_ack():
                req = urllib.request.Request(
                    url,
                    data=body,
                    method="POST",
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Content-Type": "application/json",
                    },
                )
                with urllib.request.urlopen(req, timeout=3) as response:
                    return response.status, json.loads(response.read().decode("utf-8"))

            first_status, first_payload = post_ack()
            second_status, second_payload = post_ack()

            self.assertEqual(first_status, 200)
            self.assertTrue(first_payload["ok"])
            self.assertEqual(second_status, 200)
            self.assertTrue(second_payload["ok"])
            self.assertTrue(second_payload.get("already_acked"))
            self.assertFalse(outbox_path.exists())
            self.assertTrue(sent_path.exists())

            path_after, obj_after = self.bridge.oldest_event(
                self.chat_id, self.consumer_id
            )
            self.assertIsNone(path_after)
            self.assertIsNone(obj_after)
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
