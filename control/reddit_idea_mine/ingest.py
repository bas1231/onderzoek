"""Bounded Reddit discussion ingestion for Prediction discovery; no network access.

Inputs are provided, permitted JSON exports of discussions. Outputs remain discovery
leads only; they never bypass supervisor, model or trading gates.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

SUBREDDITS = frozenset({
    "kalshi", "predictionsmarkets", "predictionmarkets",
    "polymarket", "polymarketkalshi",
})
TERMS = (
    "arbitrage", "arb", "bot", "strategy", "trading", "market making",
    "market maker", "spread", "orderbook", "order book", "liquidity",
    "fee", "weather", "sports", "latency", "settlement", "edge",
    "prediction", "backtest", "fail", "profitable", "mispricing",
)
CHALLENGES = ("doesn't", "does not", "won't", "cannot", "fees", "slippage",
              "liquidity", "risk", "stale", "wrong", "fail", "scam",
              "no edge", "not possible", "spread")
MAX_TEXT = 12000
MAX_COMMENTS = 150


def _text(value: object, limit: int = MAX_TEXT) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value).strip()[:limit]


def _discussion_id(raw: dict) -> str:
    value = _text(raw.get("id"), 120)
    if not re.fullmatch(r"[a-zA-Z0-9_-]{3,120}", value):
        raise ValueError("invalid discussion id")
    return value


def normalize(raw: dict) -> dict:
    """Normalize an explicitly supplied discussion, preserving source provenance."""
    if not isinstance(raw, dict):
        raise ValueError("discussion must be object")
    subreddit = _text(raw.get("subreddit"), 100).removeprefix("r/").lower()
    if subreddit not in SUBREDDITS:
        raise ValueError("subreddit not allowlisted")
    post_id = _discussion_id(raw)
    url = _text(raw.get("url"), 1000)
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in {"reddit.com", "www.reddit.com", "old.reddit.com"}:
        raise ValueError("invalid Reddit permalink")
    if not re.search(r"/comments/" + re.escape(post_id) + r"(?:/|$)", parsed.path, re.I):
        raise ValueError("permalink does not match id")
    title, body = _text(raw.get("title"), 300), _text(raw.get("selftext"))
    if not title:
        raise ValueError("missing title")
    comments = raw.get("comments", [])
    if not isinstance(comments, list):
        raise ValueError("comments must be array")
    comment_texts = []
    for entry in comments[:MAX_COMMENTS]:
        comment = _text(entry.get("body") if isinstance(entry, dict) else entry)
        if comment and comment not in {"[deleted]", "[removed]"}:
            comment_texts.append(comment)
    source = _text(raw.get("source"), 80)
    if source not in {"authorized_export", "manual_submission", "licensed_archive", "test_fixture", "public_archive_unverified"}:
        raise ValueError("unapproved input provenance")
    created = raw.get("created_utc")
    if not isinstance(created, (int, float)) or not 0 < created < 4102444800:
        raise ValueError("invalid UTC timestamp")
    all_text = " ".join((title, body, *comment_texts)).lower()
    matching_terms = sorted(t for t in TERMS if t in all_text)
    objections = [c for c in comment_texts if any(term in c.lower() for term in CHALLENGES)]
    fingerprint = hashlib.sha256((subreddit + "/" + post_id).encode()).hexdigest()
    return {
        "schema": "PREDICTION_REDDIT_DISCOVERY_LEAD_V1",
        "lead_id": "REDDIT-" + fingerprint[:20],
        "subreddit": subreddit,
        "post_id": post_id,
        "url": url,
        "created_at_utc": datetime.fromtimestamp(created, timezone.utc).isoformat(),
        "source_kind": source,
        "title": title,
        "body": body,
        "comments_sampled": len(comment_texts),
        "comments_total_input": len(comments),
        "comment_excerpts": comment_texts[:30],
        "counterarguments": objections[:20],
        "matched_terms": matching_terms,
        "discovery_relevant": bool(matching_terms),
        "suggested_routing": ["recon_scout", "scout"] if matching_terms else [],
        "status": "DISCOVERY_ONLY_UNVERIFIED",
        "economic_status": "NO_PROVEN_EDGE",
        "experiment_authorized": False,
        "model_review_approved": False,
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
    }


def ingest(records: list[dict]) -> dict:
    """Bounded deduplicated batch; rejects malformed records, never silently promotes."""
    if not isinstance(records, list) or len(records) > 500:
        raise ValueError("batch must be a list of at most 500")
    leads = {}
    rejected = []
    for index, raw in enumerate(records):
        try:
            lead = normalize(raw)
            leads[lead["lead_id"]] = lead
        except (ValueError, TypeError, OverflowError) as exc:
            rejected.append({"index": index, "reason": str(exc)[:150]})
    return {
        "schema": "PREDICTION_REDDIT_DISCOVERY_BATCH_V1",
        "leads": sorted(leads.values(), key=lambda item: item["lead_id"]),
        "rejected": rejected,
        "counts": {"input": len(records), "accepted_unique": len(leads), "rejected": len(rejected)},
        "economic_status": "NO_PROVEN_EDGE",
        "next_stage": "research_director_discovery_triage",
        "automatic_experiment_dispatch": False,
    }


def main(argv=None) -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    # Output path must be controlled by the isolated task executor.
    data = json.loads(args.input.read_text(encoding="utf-8"))
    result = ingest(data)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
