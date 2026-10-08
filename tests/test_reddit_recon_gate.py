import unittest
from control.reddit_idea_mine.ingest import normalize
from control.hourly.recon_candidate_bridge import eligible

DISCUSSION = {
    "id":"abc123", "subreddit":"Kalshi",
    "url":"https://www.reddit.com/r/Kalshi/comments/abc123/",
    "title":"Kalshi weather arbitrage strategy", "selftext":"Hypothesis",
    "created_utc":1791400000,
    "comments":[{"body":"Fees make it fail."}], "source":"test_fixture",
}

class RedditReconGateTests(unittest.TestCase):
    def test_reddit_is_discovery_not_recon_hunt(self):
        lead=normalize(DISCUSSION)
        self.assertTrue(lead["discovery_relevant"])
        allowed,reason=eligible(lead)
        self.assertFalse(allowed)
        self.assertEqual(reason,"status_not_hunt_or_prove")

    def test_single_reddit_thread_is_not_two_independent_sources(self):
        lead=normalize(DISCUSSION)
        finding={
            "status":"HUNT", "candidate_key":lead["lead_id"],
            "hunt_gate":{"passes":True},
            "observation_history":[{"source_id":lead["url"],
                 "document_sha256":"a"*64,"observed_at":lead["created_at_utc"]}],
            "economic_model":{"public_trigger":"weather"},
            "falsification":{"next_decisive_test":"Independent price and fee replay"},
        }
        allowed,reason=eligible(finding)
        self.assertFalse(allowed)
        self.assertEqual(reason,"insufficient_independent_evidence")

    def test_adding_comments_does_not_add_sources(self):
        finding={
            "status":"HUNT", "candidate_key":"reddit-single-thread",
            "hunt_gate":{"passes":True},
            "observation_history":[
                {"source_id":"reddit-thread", "document_sha256":"a"*64},
                {"source_id":"reddit-thread", "document_sha256":"b"*64}],
            "economic_model":{"public_trigger":"weather"},
            "falsification":{"next_decisive_test":"Test economic mechanism"},
        }
        allowed,reason=eligible(finding)
        self.assertFalse(allowed)
        self.assertEqual(reason,"insufficient_independent_evidence")

if __name__=="__main__":
    unittest.main()
