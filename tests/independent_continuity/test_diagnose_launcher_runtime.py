"""Standalone launcher path diagnosis is read-only and explicit."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from control.independent_continuity.diagnose_launcher_runtime import diagnose


class LauncherPathDiagnosisTests(unittest.TestCase):
    def setUp(self):
        self.t = TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.home = Path(self.t.name)
        self.root = self.home / ".local/share/prediction-chat-bridge"
        self.root.mkdir(parents=True)

    def test_missing_all_reports_three_missing_paths(self):
        rc, msg = diagnose(self.home)
        self.assertEqual(rc, 2)
        for name in ("sent", "routes", "dashboard_launchers"):
            self.assertIn(name + "=MISSING", msg)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_missing_only_launcher_does_not_create_it(self):
        for name in ("sent", "routes"):
            (self.root / name).mkdir()
        before = sorted(p.name for p in self.root.iterdir())
        rc, msg = diagnose(self.home)
        self.assertEqual(rc, 2)
        self.assertIn("dashboard_launchers=MISSING", msg)
        self.assertEqual(before, sorted(p.name for p in self.root.iterdir()))

    def test_existing_empty_dirs_are_distinguished_from_missing(self):
        for name in ("sent", "routes", "dashboard_launchers"):
            (self.root / name).mkdir()
        rc, msg = diagnose(self.home)
        self.assertEqual(rc, 0)
        self.assertIn("dashboard_launchers=DIR_FILES_0", msg)

    def test_symlink_is_refused(self):
        (self.root / "sent").symlink_to(self.root)
        rc, msg = diagnose(self.home)
        self.assertEqual(rc, 2)
        self.assertIn("sent=SYMLINK_REFUSED", msg)

    def test_regular_file_is_rejected(self):
        (self.root / "routes").write_text("not a directory")
        rc, msg = diagnose(self.home)
        self.assertEqual(rc, 2)
        self.assertIn("routes=NOT_DIRECTORY", msg)


if __name__ == "__main__":
    unittest.main()
