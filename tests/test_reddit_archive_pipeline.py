import json
import tempfile
import unittest
from pathlib import Path

from control.reddit_idea_mine.archive_adapter import prepare
from control.reddit_idea_mine.pipeline import run

RECORD = {
    "id": "abc123", "subreddit": "Kalshi",
    "permalink": "/r/Kalshi/comments/abc123/example/",
    "title": "Profitable weather arbitrage trading bot strategy",
    "selftext": "Market price spread and orderbook risks.",
    "comments": [{"body": "Fees and slippage erase the spread."}],
    "created_utc": 1791400000,
}

class ArchiveToReconTest(unittest.TestCase):
    def test_archive_records_go_through_real_recon_engine(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "normalized.json"
            input_path.write_text(json.dumps(prepare([RECORD], "test_fixture")))
            result = run(input_path, root, "archive-fixture-01")
            self.assertEqual(result["inputs"]["accepted_unique"], 1)
            self.assertGreater(result["recon_findings"], 0)
            self.assertEqual(result["candidate_promotions"], 0)
            self.assertEqual(result["economic_status"], "NO_PROVEN_EDGE")
            self.assertFalse((root / "knowledge/candidates").exists())

    def test_bad_provenance_denied(self):
        with self.assertRaises(ValueError):
            prepare([RECORD], "unknown_feed")

if __name__ == "__main__":
    unittest.main()
