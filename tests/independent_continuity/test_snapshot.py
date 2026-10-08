"""Git-object snapshot extraction tests; all git process calls are mocked."""
from __future__ import annotations

import io
from pathlib import Path
import tarfile
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import unittest

from control.independent_continuity.snapshot import snapshot_events, SnapshotError


def make_archive(entries):
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w:") as tf:
        for name, payload, kind in entries:
            info = tarfile.TarInfo(name)
            if kind == "file":
                info.size = len(payload)
                tf.addfile(info, io.BytesIO(payload))
            elif kind == "symlink":
                info.type = tarfile.SYMTYPE
                info.linkname = "../evil"
                tf.addfile(info)
    return out.getvalue()


class GitSnapshotTest(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "read-only-git-mirror"
        (self.repo / ".git").mkdir(parents=True)
        self.dst = self.root / "scratch"

    def fake_git(self, archive):
        def fake(argv, **kwargs):
            self.assertEqual(argv[0:3], ["git", "-C", str(self.repo)])
            self.assertNotIn("fetch", argv)
            self.assertNotIn("push", argv)
            if argv[3] == "rev-parse":
                return SimpleNamespace(stdout="a" * 40 + "\n")
            if argv[3] == "archive":
                self.assertEqual(argv[5], "a" * 40)
                return SimpleNamespace(stdout=archive)
            raise AssertionError(f"unknown process: {argv}")
        return fake

    def test_git_archive_not_working_tree_used(self):
        content = b'{"schema":"PREDICTION_BUILD_LOG_EVENT_V1"}'
        archive = make_archive([
            ("control/build_log/events/E001.json", content, "file")
        ])
        with patch("control.independent_continuity.snapshot.subprocess.run",
                   side_effect=self.fake_git(archive)):
            result = snapshot_events(self.repo, self.dst)
        self.assertEqual(result, {"source_commit": "a" * 40, "event_files": 1})
        self.assertEqual((self.dst / "E001.json").read_bytes(), content)

    def test_path_traversal_refused(self):
        archive = make_archive([
            ("control/build_log/events/../../outside.json", b"unsafe", "file")
        ])
        with patch("control.independent_continuity.snapshot.subprocess.run",
                   side_effect=self.fake_git(archive)):
            with self.assertRaisesRegex(SnapshotError, "unexpected archive entry"):
                snapshot_events(self.repo, self.dst)
        self.assertFalse((self.root / "outside.json").exists())

    def test_symlink_refused(self):
        archive = make_archive([
            ("control/build_log/events/E001.json", b"", "symlink")
        ])
        with patch("control.independent_continuity.snapshot.subprocess.run",
                   side_effect=self.fake_git(archive)):
            with self.assertRaisesRegex(SnapshotError, "non-regular"):
                snapshot_events(self.repo, self.dst)

    def test_missing_mirror_refused(self):
        (self.repo / ".git").rmdir()
        with self.assertRaisesRegex(SnapshotError, "mirror"):
            snapshot_events(self.repo, self.dst)


if __name__ == "__main__":
    unittest.main()
