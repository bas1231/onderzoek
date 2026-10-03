from __future__ import annotations

import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "control" / "tampermonkey_multichat" / "bridge_server_v2.py"


def load_base():
    spec = importlib.util.spec_from_file_location("bridge_server_v2_native_test", MODULE)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class NativeInflightAckTest(unittest.TestCase):
    def test_next_claims_inflight_and_ack_fires_hook(self):
        mod = load_base()
        with tempfile.TemporaryDirectory() as td:
            data = Path(td)
            mod.DATA_DIR = data
            mod.OUTBOX = data / "outbox"
            mod.INFLIGHT = data / "inflight"
            mod.SENT = data / "sent"
            mod.ROUTES = data / "routes"
            mod.DEFAULT_CHAT_FILE = data / "default_chat.json"
            for p in (mod.OUTBOX, mod.INFLIGHT, mod.SENT, mod.ROUTES):
                p.mkdir(parents=True, exist_ok=True)

            task_id = "NATIVE-ACK-TEST-001"
            event_id = "native-ack-event-001"
            chat_id = "chat-native-ack-001"
            consumer_id = "tab-native-ack-001"
            (mod.ROUTES / f"{task_id}.json").write_text(json.dumps({
                "version": 2,
                "task_id": task_id,
                "chat_id": chat_id,
                "consumer_id": consumer_id,
            }), encoding="utf-8")
            (mod.OUTBOX / f"{event_id}.json").write_text(json.dumps({
                "event_id": event_id,
                "task_id": task_id,
                "message": "result",
            }), encoding="utf-8")

            replies = []
            get = object.__new__(mod.Handler)
            get.path = f"/next?chat_id={chat_id}&consumer_id={consumer_id}"
            get.authorized = lambda: True
            get.reply_json = lambda status, obj: replies.append((status, obj))
            get.do_GET()

            self.assertEqual(replies[0][0], 200)
            self.assertFalse((mod.OUTBOX / f"{event_id}.json").exists())
            self.assertTrue((mod.INFLIGHT / f"{event_id}.json").exists())
            self.assertFalse((mod.SENT / f"{event_id}.json").exists())

            calls = []
            def hook(obj, *, chat_id, consumer_id, already_acked):
                calls.append((obj["event_id"], chat_id, consumer_id, already_acked))
            mod.ACK_HOOK = hook

            body = json.dumps({
                "event_id": event_id,
                "chat_id": chat_id,
                "consumer_id": consumer_id,
            }).encode("utf-8")
            ack_replies = []
            post = object.__new__(mod.Handler)
            post.path = "/ack"
            post.authorized = lambda: True
            post.headers = {"Content-Length": str(len(body))}
            post.rfile = io.BytesIO(body)
            post.reply_json = lambda status, obj: ack_replies.append((status, obj))
            post.do_POST()

            self.assertEqual(ack_replies[0][0], 200)
            self.assertFalse((mod.INFLIGHT / f"{event_id}.json").exists())
            self.assertTrue((mod.SENT / f"{event_id}.json").exists())
            self.assertEqual(calls, [(event_id, chat_id, consumer_id, False)])

            duplicate_replies = []
            post2 = object.__new__(mod.Handler)
            post2.path = "/ack"
            post2.authorized = lambda: True
            post2.headers = {"Content-Length": str(len(body))}
            post2.rfile = io.BytesIO(body)
            post2.reply_json = lambda status, obj: duplicate_replies.append((status, obj))
            post2.do_POST()

            self.assertEqual(duplicate_replies[0][0], 200)
            self.assertEqual(calls[-1], (event_id, chat_id, consumer_id, True))


if __name__ == "__main__":
    unittest.main()
