"""Independent verification for Prediction Control Room V0.

These tests build an isolated fixture repository so success does not depend on
live Research-OS state. They verify read-only HTTP behavior, safe metadata
selection and fail-closed handling of missing evidence.
"""

from __future__ import annotations

import http.client
import json
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

from control.control_room.model import build_snapshot
from control.control_room.server import make_server


class FixtureRepo:
    def __init__(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def close(self) -> None:
        self.temp.cleanup()

    def write(self, rel: str, content: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def init_git(self) -> None:
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.email", "control-room-test@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.name", "Control Room Test"], check=True)
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "--allow-empty", "-qm", "fixture"], check=True)


class ControlRoomSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = FixtureRepo()
        self.addCleanup(self.fx.close)
        self.fx.write(
            "agents/registry.json",
            json.dumps(
                {
                    "version": 4,
                    "default_status": "UNPROVEN",
                    "valid_null_result": "NO_PROVEN_EDGE",
                    "live_trading": False,
                    "paid_actions": False,
                    "wallet_actions": False,
                    "roles": [
                        {
                            "id": "research_director",
                            "authority": "RESEARCH_COORDINATION",
                            "capabilities": ["research_director"],
                            "purpose": "route evidence",
                        }
                    ],
                }
            ),
        )
        self.fx.write("PROJECT_IN_EEN_OOGOPSLAG.md", "Huidige economische status: **NO_PROVEN_EDGE**\n")
        self.fx.write(
            "control/lifecycle/TASK-E001.json",
            json.dumps(
                {
                    "task_id": "TASK-E001",
                    "hypothesis_id": "CONTROL-DASHBOARD",
                    "state": "ACCEPTED",
                    "updated_at": 1790280000.0,
                    "api_key": "SUPER-SECRET-MUST-NOT-LEAK",
                    "history": [{"state": "ACCEPTED", "at": 1790280000.0, "detail": "safe lifecycle"}],
                }
            ),
        )
        self.fx.init_git()

    def test_snapshot_exposes_safe_truth_without_secret_values(self) -> None:
        snapshot = build_snapshot(self.fx.root)
        encoded = json.dumps(snapshot)
        self.assertEqual(snapshot["schema"], "PREDICTION_CONTROL_ROOM_V0")
        self.assertEqual(snapshot["project"]["economic_status"], "NO_PROVEN_EDGE")
        self.assertIs(snapshot["project"]["live_trading"], False)
        self.assertEqual(snapshot["tasks"][0]["task_id"], "TASK-E001")
        self.assertNotIn("SUPER-SECRET-MUST-NOT-LEAK", encoded)
        self.assertNotIn("api_key", encoded.lower())
        self.assertFalse(snapshot["dashboard"]["outbound_network_calls"])
        self.assertFalse(snapshot["dashboard"]["mutation_endpoints"])

    def test_missing_evidence_is_warning_not_healthy_inference(self) -> None:
        empty = FixtureRepo()
        self.addCleanup(empty.close)
        empty.init_git()
        snapshot = build_snapshot(empty.root)
        self.assertEqual(snapshot["project"]["economic_status"], "UNKNOWN")
        self.assertEqual(snapshot["system_health"]["status"], "WARNING")
        codes = {item["code"] for item in snapshot["alerts"]}
        self.assertIn("ECONOMIC_STATUS_UNKNOWN", codes)
        self.assertIn("NO_RUNTIME_EVIDENCE", codes)

    def test_agent_without_runtime_evidence_stays_unknown(self) -> None:
        (self.fx.root / "control/lifecycle/TASK-E001.json").unlink()
        snapshot = build_snapshot(self.fx.root)
        self.assertEqual(snapshot["agents"][0]["runtime_status"], "UNKNOWN_NO_HEARTBEAT")


class ControlRoomHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = FixtureRepo()
        self.addCleanup(self.fx.close)
        self.fx.write(
            "agents/registry.json",
            json.dumps({"live_trading": False, "paid_actions": False, "wallet_actions": False, "valid_null_result": "NO_PROVEN_EDGE", "roles": []}),
        )
        self.fx.init_git()
        self.server = make_server(self.fx.root, host="127.0.0.1", port=0, quiet=True)
        self.addCleanup(self.server.server_close)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self._stop)
        self.host, self.port = self.server.server_address

    def _stop(self) -> None:
        self.server.shutdown()
        self.thread.join(timeout=2)

    def request(self, method: str, path: str):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=2)
        conn.request(method, path)
        response = conn.getresponse()
        body = response.read()
        headers = dict(response.getheaders())
        conn.close()
        return response.status, headers, body

    def test_health_and_snapshot_are_get_only(self) -> None:
        status, _, body = self.request("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body)["read_only"])

        status, _, body = self.request("GET", "/api/snapshot")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["schema"], "PREDICTION_CONTROL_ROOM_V0")

        for method in ("POST", "PUT", "PATCH", "DELETE"):
            status, headers, body = self.request(method, "/api/snapshot")
            self.assertEqual(status, 405, method)
            self.assertEqual(headers.get("Allow"), "GET, HEAD")
            self.assertTrue(json.loads(body)["read_only"])

    def test_static_surface_has_local_security_headers(self) -> None:
        status, headers, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"CONTROL ROOM", body)
        self.assertEqual(headers.get("X-Frame-Options"), "DENY")
        self.assertIn("default-src 'self'", headers.get("Content-Security-Policy", ""))
        status, _, _ = self.request("GET", "/not-allowed.txt")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
