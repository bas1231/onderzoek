import unittest
from control.reddit_idea_mine.ingest import ingest
from control.reddit_idea_mine.recon_handoff import to_recon_routing, preview

POST={"id":"abc123","subreddit":"Kalshi",
"url":"https://www.reddit.com/r/Kalshi/comments/abc123/",
"title":"Profitable weather arbitrage trading bot strategy",
"selftext":"The market price spread and orderbook show risks in settlement.",
"comments":[{"body":"Fees and slippage erase the spread."}],
"created_utc":1791400000,"source":"test_fixture"}

class RedditReconHandoffTest(unittest.TestCase):
    def test_real_recon_engine_receives_discovery(self):
        batch=ingest([POST])
        result=preview(batch)
        self.assertEqual(result["evidence_count"],1)
        self.assertGreater(len(result["findings"]),0)
        self.assertFalse(result["candidate_created"])
        self.assertFalse(result["watchlist_written"])
        self.assertEqual(result["scientific_status"],"NO_PROVEN_EDGE")

    def test_repeated_commenters_still_one_source(self):
        batch=ingest([{**POST,"comments":[{"body":"Too many fees."}]*20}])
        routing=to_recon_routing(batch)
        self.assertEqual(len(routing["recon_scout"]["evidence"]),1)

    def test_deny_tampered_lead(self):
        batch=ingest([POST])
        batch["leads"][0]["economic_status"]="PROVEN_EDGE"
        with self.assertRaises(ValueError):
            preview(batch)

    def test_irrelevant_lead_not_routed(self):
        batch=ingest([{**POST,"title":"Hello everyone","selftext":"","comments":[]}])
        self.assertEqual(preview(batch)["evidence_count"],0)

if __name__=="__main__":
    unittest.main()
