import unittest
from datetime import datetime, timezone
from control.reddit_idea_mine.freshness import report

class FreshnessTests(unittest.TestCase):
    def test_recent_and_old_posts(self):
        batch={"schema":"PREDICTION_REDDIT_DISCOVERY_BATCH_V1","leads":[
          {"created_at_utc":"2026-10-08T17:55:00+00:00"},
          {"created_at_utc":"2026-10-08T15:00:00+00:00"}]}
        result=report(batch,datetime(2026,10,8,18,0,tzinfo=timezone.utc))
        self.assertEqual(result["fresh_under_horizon"],1)
        self.assertEqual(result["median_age_minutes"],92.5)
        self.assertFalse(result["timeliness_proven"])

    def test_future_clock_rejected(self):
        batch={"schema":"PREDICTION_REDDIT_DISCOVERY_BATCH_V1",
          "leads":[{"created_at_utc":"2026-10-08T18:10:00+00:00"}]}
        result=report(batch,datetime(2026,10,8,18,0,tzinfo=timezone.utc))
        self.assertEqual(result["future_timestamp_rejected"],1)
        self.assertIsNone(result["median_age_minutes"])

    def test_reject_invalid_batch(self):
        with self.assertRaises(ValueError):
            report({"schema":"incorrect"})
if __name__=="__main__":
    unittest.main()
