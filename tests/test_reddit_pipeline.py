import json
import tempfile
import unittest
from pathlib import Path

from control.reddit_idea_mine.pipeline import run
from control.reddit_idea_mine.ingest import ingest
from control.reddit_idea_mine.recon_handoff import to_recon_routing

POST={"id":"abc123","subreddit":"Kalshi",
"url":"https://www.reddit.com/r/Kalshi/comments/abc123/",
"title":"Profitable weather arbitrage trading bot strategy",
"selftext":"Market price spread and orderbook risks.",
"comments":[{"body":"Fees and slippage erase the spread."}],
"created_utc":1791400000,"source":"test_fixture"}

class RedditPipelineTest(unittest.TestCase):
    def test_persistent_run_remains_discovery(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            inp=root/"threads.json"
            inp.write_text(json.dumps([POST]))
            receipt=run(inp,root,"fixture-001")
            self.assertEqual(receipt["inputs"]["accepted_unique"],1)
            self.assertGreater(receipt["recon_findings"],0)
            self.assertEqual(receipt["candidate_promotions"],0)
            self.assertEqual(receipt["economic_status"],"NO_PROVEN_EDGE")
            self.assertFalse((root/"knowledge/candidates").exists())
            self.assertTrue((root/receipt["recon_ref"]).exists())
            with self.assertRaises(FileExistsError):
                run(inp,root,"fixture-001")

    def test_publication_and_observation_times_distinct(self):
        routing=to_recon_routing(ingest([POST]))
        evidence=routing["recon_scout"]["evidence"][0]
        self.assertEqual(evidence["original_post_created_at"],"2026-10-07T18:13:20+00:00")
        self.assertNotEqual(evidence["retrieved_at"],evidence["original_post_created_at"])

    def test_disallows_unsafe_run_id(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            inp=root/"threads.json"
            inp.write_text(json.dumps([POST]))
            with self.assertRaises(ValueError):
                run(inp,root,"../escape")

if __name__=="__main__":
    unittest.main()
