from __future__ import annotations

import importlib
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class SnapshotExportDeliveryTests(unittest.TestCase):
    def test_hardened_bridge_preserves_bounded_export_payload(self):
        hardened = importlib.import_module("bridge_server_hardened")
        data = "A" * 24000
        meta = '{"archive_sha256":"abc","base64_chars":24000,"offset":0,"chunk_chars":24000,"final":true}'
        obj = {
            "task_id": "DEV-PRED-PRODUCTION-EXPORT-E001",
            "event_id": "evt-1",
            "message": (
                "DEV_TASK_STATUS=PASS\n"
                "PREDICTION_SNAPSHOT_EXPORT_V1\n"
                f"SNAPSHOT_EXPORT_META={meta}\n"
                f"SNAPSHOT_EXPORT_DATA={data}\n"
            ),
        }
        out = hardened.compact_delivery_event(obj)
        self.assertTrue(out["snapshot_export_delivery"])
        self.assertTrue(out["message"].startswith("PREDICTION_SNAPSHOT_EXPORT_V1 task="))
        self.assertIn(" data=" + data, out["message"])
        self.assertLessEqual(len(out["message"]), hardened.MAX_SNAPSHOT_EXPORT_MESSAGE)

    def test_hardened_bridge_rejects_oversized_export_payload(self):
        hardened = importlib.import_module("bridge_server_hardened")
        data = "A" * 26000
        obj = {
            "task_id": "DEV-PRED-PRODUCTION-EXPORT-E002",
            "event_id": "evt-2",
            "message": (
                "DEV_TASK_STATUS=PASS\n"
                "PREDICTION_SNAPSHOT_EXPORT_V1\n"
                'SNAPSHOT_EXPORT_META={"offset":0}\n'
                f"SNAPSHOT_EXPORT_DATA={data}\n"
            ),
        }
        out = hardened.compact_delivery_event(obj)
        self.assertIn("EXPORT_CHUNK_TOO_LARGE", out["message"])
        self.assertNotIn(" data=" + data, out["message"])

    def test_normal_wsl_delivery_keeps_existing_900_char_limit(self):
        hardened = importlib.import_module("bridge_server_hardened")
        obj = {
            "task_id": "DEV-PRED-NORMAL-E001",
            "event_id": "evt-3",
            "message": "DEV_TASK_STATUS=FAIL\nERROR_CLASS=" + ("X" * 5000),
        }
        out = hardened.compact_delivery_event(obj)
        self.assertLessEqual(len(out["message"]), hardened.MAX_BROWSER_MESSAGE)
        self.assertFalse(out.get("snapshot_export_delivery", False))

    def test_all_compaction_layers_contain_export_guard(self):
        for name in (
            "bridge_server_hardened.py",
            "bridge_server_status_compaction.py",
            "bridge_server_status_compaction_v11.py",
        ):
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn("PREDICTION_SNAPSHOT_EXPORT_V1", text)
            self.assertIn("MAX_SNAPSHOT_EXPORT_MESSAGE", text)
            self.assertIn("EXPORT_CHUNK_TOO_LARGE", text)


if __name__ == "__main__":
    unittest.main()
