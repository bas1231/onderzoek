"""Synthetic safety tests for read-only installed wake launcher diagnostics."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from control.independent_continuity.diagnose_installed_launcher_support import classify


class InstalledLauncherDiagnosisTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name)
        self.root = self.home / ".local/share/prediction-chat-bridge"
        self.root.mkdir(parents=True)
        
    def write(self, name, value):
        (self.root / name).write_text(value, encoding="utf-8")

    def test_empty_runtime_read_only_failure(self):
        before = list(self.root.iterdir())
        rc, detail = classify(self.home)
        self.assertEqual(rc, 2)
        self.assertIn("bridge_server_py=MISSING", detail)
        self.assertIn("prediction_chat_wake_user_js=MISSING", detail)
        self.assertEqual(before, list(self.root.iterdir()))

    def test_supported_server_and_script(self):
        self.write("bridge_server.py", "import bridge_server_session_bootstrap as session")
        self.write("bridge_server_session_bootstrap.py",
                   "def register_dashboard_launcher(): pass\n# /dashboard-launcher/register")
        self.write("prediction-chat-wake.user.js",
                   "// @version 0.5.0\nconst url = '/dashboard-launcher/register';")
        before = {p.name:p.read_bytes() for p in self.root.iterdir()}
        rc, detail = classify(self.home)
        self.assertEqual(rc, 0)
        self.assertIn("bridge_server_py=SESSION_CAPABLE", detail)
        self.assertIn("bridge_server_session_bootstrap_py=REGISTRATION_ENDPOINT_PRESENT", detail)
        self.assertIn("prediction_chat_wake_user_js=REGISTRATION_CODE_0.5.0", detail)
        self.assertEqual(before, {p.name:p.read_bytes() for p in self.root.iterdir()})

    def test_old_script_reported_without_speculation(self):
        self.write("bridge_server.py", "import bridge_server_session_bootstrap")
        self.write("bridge_server_session_bootstrap.py",
                   "register_dashboard_launcher\n/dashboard-launcher/register")
        self.write("prediction-chat-wake.user.js", "// @version 0.4.8")
        rc, detail = classify(self.home)
        self.assertEqual(rc, 0)
        self.assertIn("prediction_chat_wake_user_js=NO_REGISTRATION_CODE_0.4.8", detail)

    def test_missing_bootstrap_endpoint_is_failure(self):
        self.write("bridge_server.py", "import bridge_server_session_bootstrap")
        self.write("bridge_server_session_bootstrap.py", "# old code")
        rc, detail = classify(self.home)
        self.assertEqual(rc, 2)
        self.assertIn("REGISTRATION_ENDPOINT_ABSENT", detail)

    def test_symlink_refusal(self):
        self.write("bridge_server.py", "import bridge_server_session_bootstrap")
        (self.root / "bridge_server_session_bootstrap.py").symlink_to(self.root / "bridge_server.py")
        rc, detail = classify(self.home)
        self.assertEqual(rc, 2)
        self.assertIn("SYMLINK_REFUSED", detail)


if __name__ == "__main__":
    unittest.main()
