import json
import tempfile
import unittest
from pathlib import Path
from control.reddit_idea_mine.source_inbox import process

POST={"id":"abc123","subreddit":"Kalshi",
"url":"https://www.reddit.com/r/Kalshi/comments/abc123/",
"title":"Profitable weather arbitrage trading bot strategy",
"selftext":"Market price spread and orderbook risks.",
"comments":[{"body":"Fees and slippage erase the spread."}],
"created_utc":1791400000,"source":"test_fixture"}

class RedditInboxTests(unittest.TestCase):
    def test_process_once_and_keep_gates(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            inbox=base/"inbox"
            inbox.mkdir()
            (inbox/"batch001.json").write_text(json.dumps([POST]))
            first=process(inbox,base)
            self.assertEqual(first["results"][0]["status"],"PROCESSED")
            second=process(inbox,base)
            self.assertEqual(second["results"][0]["status"],"ALREADY_PROCESSED")
            self.assertFalse((base/"knowledge/candidates").exists())
            self.assertEqual(first["economic_conclusion"],"NO_PROVEN_EDGE")

    def test_invalid_payload_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp); inbox=base/"inbox"; inbox.mkdir()
            (inbox/"invalid.json").write_text("{bad")
            self.assertEqual(process(inbox,base)["results"][0]["status"],"REJECTED")

    def test_bounded(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp); inbox=base/"inbox"; inbox.mkdir()
            with self.assertRaises(ValueError):
                process(inbox,base,21)

if __name__ == "__main__":
    unittest.main()
