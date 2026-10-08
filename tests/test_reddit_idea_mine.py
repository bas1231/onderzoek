import unittest
from control.reddit_idea_mine.ingest import ingest, normalize

BASE = {"id":"abc123","subreddit":"Kalshi","url":"https://www.reddit.com/r/Kalshi/comments/abc123/example/","title":"Weather arbitrage strategy","selftext":"Investigate edge","created_utc":1791400000,"comments":[{"body":"Fees and slippage make this fail."},{"body":"Try another settlement method."}],"source":"test_fixture"}

class RedditIdeaMineTest(unittest.TestCase):
    def test_criticisms_and_gates(self):
        r=normalize(BASE)
        self.assertEqual(r["comments_sampled"],2)
        self.assertEqual(len(r["counterarguments"]),1)
        self.assertEqual(r["economic_status"],"NO_PROVEN_EDGE")
        self.assertFalse(r["experiment_authorized"])
        self.assertFalse(r["model_review_approved"])
        self.assertFalse(r["live_trading"])

    def test_dedupe(self):
        self.assertEqual(ingest([BASE,BASE])["counts"]["accepted_unique"],1)

    def test_subreddit_exclusion(self):
        self.assertEqual(ingest([{**BASE,"subreddit":"unlisted"}])["counts"]["rejected"],1)

    def test_url_verification(self):
        self.assertEqual(ingest([{**BASE,"url":"https://example.org/comments/abc123"}])["counts"]["rejected"],1)

    def test_source_provenance(self):
        self.assertEqual(ingest([{**BASE,"source":"unknown_scrape"}])["counts"]["rejected"],1)

    def test_batch_bound(self):
        with self.assertRaises(ValueError): ingest([BASE]*501)

    def test_not_relevant(self):
        r=normalize({**BASE,"title":"Hello everyone","selftext":"","comments":[]})
        self.assertEqual(r["suggested_routing"],[])

if __name__ == "__main__":
    unittest.main()
