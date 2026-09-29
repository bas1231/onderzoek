from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TM = ROOT / "control" / "tampermonkey_multichat"
BUS = ROOT / "control" / "bridge_commands"


def load_as(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class ActivePageRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router_base = load_as("command_router_base", TM / "command_router.py")
        cls.router = load_as("command_router_active_page_test", TM / "command_router_active_page.py")
        cls.poller_base = load_as("command_bus_poller_base", BUS / "command_bus_poller.py")
        cls.poller = load_as("command_bus_poller_active_page_test", BUS / "command_bus_poller_active_page.py")
        cls.patcher = load_as("patch_v050_active_page_test", TM / "patch_v050_active_page.py")

    def test_presence_claim_and_self_clear(self):
        with tempfile.TemporaryDirectory() as td:
            active = Path(td) / "active_page.json"
            old = self.router.ACTIVE_PAGE_FILE
            self.router.ACTIVE_PAGE_FILE = active
            try:
                claimed = self.router.update_presence("chat-test-1234", "tab-test-1234", True, True)
                self.assertTrue(claimed["active"])
                stored = json.loads(active.read_text())
                self.assertEqual(stored["chat_id"], "chat-test-1234")
                self.assertEqual(stored["consumer_id"], "tab-test-1234")
                cleared = self.router.update_presence("chat-test-1234", "tab-test-1234", False, True)
                self.assertFalse(cleared["active"])
            finally:
                self.router.ACTIVE_PAGE_FILE = old

    def test_background_tab_cannot_clear_foreground_binding(self):
        with tempfile.TemporaryDirectory() as td:
            active = Path(td) / "active_page.json"
            old = self.router.ACTIVE_PAGE_FILE
            self.router.ACTIVE_PAGE_FILE = active
            try:
                self.router.update_presence("chat-a-1234", "tab-a-1234", True, True)
                self.router.update_presence("chat-b-1234", "tab-b-1234", False, True)
                stored = json.loads(active.read_text())
                self.assertTrue(stored["active"])
                self.assertEqual(stored["chat_id"], "chat-a-1234")
            finally:
                self.router.ACTIVE_PAGE_FILE = old

    def test_poller_prefers_fresh_active_page_and_fails_closed_when_stale(self):
        with tempfile.TemporaryDirectory() as td:
            active = Path(td) / "active_page.json"
            old = self.poller.ACTIVE_PAGE_FILE
            self.poller.ACTIVE_PAGE_FILE = active
            try:
                active.write_text(json.dumps({
                    "active": True,
                    "chat_id": "chat-route-1234",
                    "consumer_id": "tab-route-1234",
                    "updated_at_unix": time.time(),
                }))
                route, source = self.poller.resolve_route({"notes": ""})
                self.assertEqual(source, "active_page")
                self.assertEqual(route, {"chat_id": "chat-route-1234", "consumer_id": "tab-route-1234"})

                active.write_text(json.dumps({
                    "active": True,
                    "chat_id": "chat-route-1234",
                    "consumer_id": "tab-route-1234",
                    "updated_at_unix": time.time() - 60,
                }))
                route, source = self.poller.resolve_route({"notes": ""})
                self.assertIsNone(route)
                self.assertEqual(source, "active_page_required")
            finally:
                self.poller.ACTIVE_PAGE_FILE = old

    def test_userscript_patch_adds_focus_presence_and_update_url(self):
        source = (TM / "prediction-chat-wake.user.js").read_text(encoding="utf-8")
        out = self.patcher.transform(source)
        self.assertIn("// @version      0.5.0", out)
        self.assertIn("async function publishPresence()", out)
        self.assertIn("`${COMMAND_BASE}/presence`", out)
        self.assertIn("document.hasFocus()", out)
        self.assertIn("setInterval(publishPresence, 2000)", out)
        self.assertIn("@updateURL    http://localhost:8765/prediction-chat-wake.user.js", out)


if __name__ == "__main__":
    unittest.main()
