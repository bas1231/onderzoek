import unittest
from datetime import datetime, timezone
from control.reddit_idea_mine.source_canary import probe, POSTS

NOW=datetime(2026,10,8,18,0,tzinfo=timezone.utc)

def served(ts):
    def getter(path, params):
        assert path == POSTS
        assert params == {"subreddit":"kalshi","limit":3,"sort":"desc"}
        return {"data":[{"id":"xyz123","subreddit":"Kalshi","created_utc":ts}]}
    return getter

class ArcticCanaryTests(unittest.TestCase):
    def test_recent_valid_data(self):
        result=probe(served(NOW.timestamp()-3600),now=NOW)
        self.assertEqual(result["status"],"DATA_OBSERVED")
        self.assertEqual(result["newest_post_age_minutes"],60.0)
        self.assertEqual(result["requests"],1)
        self.assertEqual(result["economic_conclusion"],"NO_PROVEN_EDGE")

    def test_archive_ingest_lag_from_api_retrieved_on(self):
        created = NOW.timestamp() - 3600
        def archive(path, params):
            return {"data": [{"subreddit": "Kalshi",
                             "created_utc": created,
                             "retrieved_on": created + 180}]}
        result = probe(archive, now=NOW)
        self.assertEqual(result["status"], "FRESH_DATA_OBSERVED")
        self.assertTrue(result["archive_timestamp_observed"])
        self.assertEqual(result["archive_ingest_lag_minutes"], 3.0)
        self.assertEqual(result["archive_to_probe_minutes"], 57.0)

    def test_archive_timestamp_missing_or_future_not_faked(self):
        created = NOW.timestamp() - 3600
        result = probe(served(created), now=NOW)
        self.assertFalse(result["archive_timestamp_observed"])
        self.assertIsNone(result["archive_ingest_lag_minutes"])
        def future(path, params):
            return {"data": [{"subreddit":"Kalshi",
                             "created_utc": created,
                             "retrieved_on": NOW.timestamp() + 500}]}
        result = probe(future, now=NOW)
        self.assertFalse(result["archive_timestamp_observed"])

    def test_stale_data(self):
        result=probe(served(NOW.timestamp()-35*24*3600),now=NOW)
        self.assertEqual(result["status"],"DATA_OBSERVED")
        self.assertGreater(result["newest_post_age_minutes"],30*24*60)

    def test_failure_is_fail_closed(self):
        def fail(*_):
            raise TimeoutError("remote API unavailable")
        result=probe(fail,now=NOW)
        self.assertEqual(result["status"],"SOURCE_FAILURE")
        self.assertEqual(result["error_type"],"TimeoutError")
        self.assertNotIn("remote API unavailable",str(result))

    def test_invalid_and_future(self):
        self.assertEqual(probe(lambda *_:{"data":[{"subreddit":"kalshi","created_utc":NOW.timestamp()+500}]},now=NOW)["status"],"EMPTY_OR_INVALID")
        self.assertEqual(probe(lambda *_:{"data":"wrong"},now=NOW)["status"],"SOURCE_FAILURE")

    def test_no_request_when_clock_naive(self):
        def forbidden(*_):
            raise AssertionError("fetch must not happen")
        with self.assertRaises(ValueError):
            probe(forbidden,now=datetime(2026,10,8,18,0))

if __name__=="__main__":
    unittest.main()
