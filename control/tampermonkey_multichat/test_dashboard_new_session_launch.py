from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import bridge_server_session_bootstrap as mod


class DashboardNewSessionLaunchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        mod.base.DATA_DIR = root
        mod.base.OUTBOX = root / "outbox"
        mod.base.SENT = root / "sent"
        mod.base.ROUTES = root / "routes"
        mod.base.INFLIGHT = root / "inflight"
        for path in (
            mod.base.OUTBOX,
            mod.base.SENT,
            mod.base.ROUTES,
            mod.base.INFLIGHT,
            mod._dashboard_launchers_dir(),
            mod._dashboard_launches_dir(),
        ):
            path.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_project_launcher_registration_is_scoped_and_capability_marked(self):
        record = mod.register_dashboard_launcher({
            "chat_id": "chat-c-abcdef12-24",
            "consumer_id": "tab-abcdef123456",
            "launch_base_url": "https://chatgpt.com/g/g-p-prediction",
            "script_version": "0.5.0",
        })
        self.assertEqual(record["chat_id"], "chat-c-abcdef12-24")
        self.assertEqual(record["consumer_id"], "tab-abcdef123456")
        self.assertEqual(record["launch_base_url"], "https://chatgpt.com/g/g-p-prediction")
        self.assertIn("dashboard_new_session_launch_v1", record["capabilities"])
        self.assertEqual(len(list(mod._dashboard_launchers_dir().glob("*.json"))), 1)

    def test_standalone_chat_root_cannot_register_as_project_launcher(self):
        with self.assertRaises(ValueError):
            mod.register_dashboard_launcher({
                "chat_id": "chat-c-abcdef12-24",
                "consumer_id": "tab-abcdef123456",
                "launch_base_url": "https://chatgpt.com/",
                "script_version": "0.5.0",
            })

    def test_launch_payload_round_trip_and_ack(self):
        token = "abcDEF0123456789_xyz"
        payload = {
            "schema": "PREDICTION_DASHBOARD_CHAT_LAUNCH_V1",
            "launch_token": token,
            "request_id": "SYNC-TEST",
            "action": "SYNC",
            "work_item_id": "PRODUCTION-RECONCILIATION-20261005",
            "prompt": "PREDICTION_CONTROL_SYNC_REQUEST_V2",
            "launch_base_url": "https://chatgpt.com/g/g-p-prediction",
            "state": "QUEUED",
        }
        mod._atomic_json(mod._dashboard_launches_dir() / f"{token}.json", payload)
        loaded = mod.load_dashboard_launch(token)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["prompt"], "PREDICTION_CONTROL_SYNC_REQUEST_V2")
        acked = mod.acknowledge_dashboard_launch(token)
        self.assertEqual(acked["state"], "PROMPT_SUBMITTED")
        reread = json.loads(
            (mod._dashboard_launches_dir() / f"{token}.json").read_text(encoding="utf-8")
        )
        self.assertEqual(reread["state"], "PROMPT_SUBMITTED")

    def test_userscript_contains_new_session_control_path(self):
        script = (HERE / "prediction-chat-wake.user.js").read_text(encoding="utf-8")
        for expected in (
            "@version      0.5.0",
            "@grant        GM_openInTab",
            "DASHBOARD_NEW_SESSION_LAUNCH_V1",
            "registerDashboardLauncher",
            "consumeDashboardLaunch",
            "prediction_launch",
            "GM_openInTab",
        ):
            self.assertIn(expected, script)


if __name__ == "__main__":
    unittest.main()
