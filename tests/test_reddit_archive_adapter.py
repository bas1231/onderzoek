import unittest
from control.reddit_idea_mine.archive_adapter import convert

RECORD={
 "id":"abc123", "subreddit":"Kalshi",
 "permalink":"/r/Kalshi/comments/abc123/test/",
 "title":"Trading arbitrage strategy", "selftext":"Weather market spread",
 "created_utc":1791400000, "comments":[{"body":"Fees and slippage kill this"}]
}
class ArchiveAdapterTest(unittest.TestCase):
 def test_normalizes_relative_link(self):
  result=convert([RECORD],"test_fixture")
  self.assertEqual(result["counts"]["accepted_unique"],1)
  self.assertEqual(result["leads"][0]["economic_status"],"NO_PROVEN_EDGE")
  self.assertEqual(result["leads"][0]["comments_sampled"],1)
 def test_provenance_guard(self):
  with self.assertRaises(ValueError):
   convert([RECORD],"unauthorized_scrape")
 def test_invalid_record_rejected(self):
  result=convert([{**RECORD,"subreddit":"other"}],"test_fixture")
  self.assertEqual(result["counts"]["rejected"],1)
 def test_batch_bound(self):
  with self.assertRaises(ValueError):
   convert([RECORD]*501,"test_fixture")
if __name__=="__main__":
 unittest.main()
