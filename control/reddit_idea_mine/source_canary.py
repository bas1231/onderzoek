"""Single-request, read-only reachability/freshness probe for Arctic Shift.

Only metadata (counts/age/error type) is returned; never writes post text or
credentials, never launches subprocesses, never places orders. This can be run
from an explicitly permitted Prediction runtime. Qualification uses a fixture
fetch callback; the scoped project executor's network guard remains intact.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from control.reddit_idea_mine.arctic_shift_source import POSTS, https_json

SOURCE = "kalshi"
MAX_AGE_MINUTES = 24 * 60


def probe(fetch=None, *, now: datetime | None = None) -> dict:
    clock = now or datetime.now(timezone.utc)
    if clock.tzinfo is None:
        raise ValueError("aware clock required")
    get = fetch or https_json
    output = {
        "schema": "PREDICTION_ARCTIC_SHIFT_SOURCE_CANARY_V1",
        "source": "arctic_shift",
        "subreddit": SOURCE,
        "observed_at_utc": clock.astimezone(timezone.utc).isoformat(),
        "requests": 1,
        "records_seen": 0,
        "newest_post_age_minutes": None,
        "archive_ingest_lag_minutes": None,
        "archive_to_probe_minutes": None,
        "archive_timestamp_observed": False,
        "status": "UNVERIFIED",
        "economic_conclusion": "NO_PROVEN_EDGE",
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
    }
    try:
        response = get(POSTS, {
            "subreddit": SOURCE, "limit": 3, "sort": "desc",
        })
        posts = response.get("data") if isinstance(response, dict) else None
        if not isinstance(posts, list):
            raise ValueError("invalid API response")
        ages = []
        newest = None
        for post in posts[:3]:
            if not isinstance(post, dict):
                continue
            if str(post.get("subreddit", "")).lower() != SOURCE:
                continue
            ts = post.get("created_utc")
            if type(ts) not in (int, float) or not 0 < ts < 4102444800:
                continue
            age = (clock.timestamp() - ts) / 60
            if age < -2:
                continue
            ages.append(max(0.0, age))
            if newest is None or ts > newest["created"]:
                archived = post.get("retrieved_on")
                newest = {"created": ts, "archived": archived}
        output["records_seen"] = len(ages)
        if not ages:
            output["status"] = "EMPTY_OR_INVALID"
        else:
            output["newest_post_age_minutes"] = round(min(ages), 2)
            archived = newest["archived"]
            created = newest["created"]
            if (type(archived) in (float, int)
                    and created - 120 <= archived <= clock.timestamp() + 120):
                output["archive_timestamp_observed"] = True
                output["archive_ingest_lag_minutes"] = round(
                    max(0.0, (archived - created) / 60), 2)
                output["archive_to_probe_minutes"] = round(
                    max(0.0, (clock.timestamp() - archived) / 60), 2)
            output["status"] = (
                "FRESH_DATA_OBSERVED" if min(ages) <= MAX_AGE_MINUTES
                else "STALE_DATA_OBSERVED"
            )
    except (OSError, TimeoutError, ValueError, TypeError, KeyError,
            json.JSONDecodeError) as exc:
        output["status"] = "SOURCE_FAILURE"
        output["error_type"] = type(exc).__name__
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args()
    print(json.dumps(probe(), sort_keys=True))


if __name__ == "__main__":
    main()
