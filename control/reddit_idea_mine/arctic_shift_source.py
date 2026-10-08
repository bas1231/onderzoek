"""Read-only, bounded Arctic Shift data source for Reddit Idea Mine.

No third-party dependencies, subprocesses, executable content, login, credentials
or trading. Network requests are pinned to one HTTPS host and two paths. The
Prediction project executor's network guard is NOT bypassed: its tests pass an
in-memory fetcher; deployment needs a separately permitted network runtime.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import ssl
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import (
    HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener,
)

from control.reddit_idea_mine.ingest import SUBREDDITS, TERMS

HOST = "arctic-shift.photon-reddit.com"
BASE = "https://" + HOST
POSTS = "/api/posts/search"
COMMENTS = "/api/comments/search"
MAX_BYTES = 2_000_000
MAX_POSTS_PER_SUB = 20
MAX_COMMENT_QUERIES = 8
MAX_COMMENTS_PER_POST = 20
HTTP_TIMEOUT = 12


class _NeverRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def https_json(path: str, params: dict[str, str | int]) -> dict:
    """No caller-defined hosts, paths, proxies, redirects, cookies or auth."""
    if path not in {POSTS, COMMENTS}:
        raise ValueError("API endpoint not allowlisted")
    if any(not isinstance(k, str) or not isinstance(v, (str, int))
           for k, v in params.items()):
        raise ValueError("invalid request parameters")
    url = BASE + path + "?" + urlencode(params)
    req = Request(url, headers={
        "User-Agent": "Prediction-Research-ReadOnly/1.0",
        "Accept": "application/json",
        "Accept-Encoding": "identity",
    }, method="GET")
    opener = build_opener(
        ProxyHandler({}), HTTPSHandler(context=ssl.create_default_context()),
        _NeverRedirect(),
    )
    with opener.open(req, timeout=HTTP_TIMEOUT) as response:
        if not response.headers.get("Content-Type", "").lower().startswith("application/json"):
            raise ValueError("unexpected media type")
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("response exceeds byte limit")
    parsed = json.loads(raw.decode("utf-8"))
    if not isinstance(parsed, dict) or not isinstance(parsed.get("data"), list):
        raise ValueError("unexpected API envelope")
    return parsed


def _entries(envelope: dict, label: str) -> list:
    if not isinstance(envelope, dict) or not isinstance(envelope.get("data"), list):
        raise ValueError("invalid " + label + " data")
    return envelope["data"]


def collect(fetch=None, *, now: datetime | None = None,
            lookback_hours: int = 168, limit: int = 15,
            comment_budget: int = 8) -> dict:
    """Bounded one-shot discovery; fail closed for malformed data.

    In test mode fetch(path, params) is a fixture; the production default is
    the fixed-host HTTPS fetcher. Each post is one independent Recon source.
    """
    if not 1 <= lookback_hours <= 24 * 30 or not 1 <= limit <= MAX_POSTS_PER_SUB:
        raise ValueError("unsafe search settings")
    if not 0 <= comment_budget <= MAX_COMMENT_QUERIES:
        raise ValueError("unsafe comment budget")
    clock = now or datetime.now(timezone.utc)
    if clock.tzinfo is None:
        raise ValueError("timezone-aware clock required")
    clock = clock.astimezone(timezone.utc)
    cutoff = clock - timedelta(hours=lookback_hours)
    get = fetch or https_json
    records = []
    errors = []
    for sub in sorted(SUBREDDITS):
        params = {
            "subreddit": sub, "after": cutoff.strftime("%Y-%m-%d"),
            "limit": limit, "sort": "desc",
        }
        try:
            posts = _entries(get(POSTS, params), "posts")
        except (OSError, ValueError, TimeoutError, json.JSONDecodeError) as exc:
            errors.append({"subreddit": sub, "error": type(exc).__name__})
            continue
        for post in posts[:limit]:
            if not isinstance(post, dict):
                continue
            pid = post.get("id")
            ts = post.get("created_utc")
            title = post.get("title")
            if (not isinstance(pid, str) or
                    not re.fullmatch(r"[A-Za-z0-9_-]{3,120}", pid) or
                    not isinstance(ts, (int, float)) or
                    isinstance(ts, bool) or
                    not isinstance(title, str) or not title.strip()):
                continue
            # Server date filters are coarse, so also enforce a precise cutoff.
            if not cutoff.timestamp() <= ts <= clock.timestamp() + 120:
                continue
            if str(post.get("subreddit", "")).lower() != sub:
                continue
            records.append({
                "id": pid, "subreddit": sub,
                "url": "https://www.reddit.com/r/" + sub + "/comments/" + pid + "/",
                "title": title[:300], "selftext": str(post.get("selftext") or "")[:12000],
                "created_utc": ts, "comments": [],
                "source": "public_archive_unverified",
            })
    # Preserve one record per thread, even if API windows overlap.
    unique = {(p["subreddit"], p["id"]): p for p in records}
    # Fair, bounded comment enrichment: do not spend the entire comment
    # budget on the alphabetically first subreddit. Rotate priority hourly,
    # so smaller communities get sampled across recurring research cycles.
    subs = sorted(SUBREDDITS)
    offset = int(clock.timestamp() // 3600) % len(subs)
    order = subs[offset:] + subs[:offset]
    queues = {sub: [] for sub in subs}
    for post in unique.values():
        queues[post["subreddit"]].append(post)
    for sub in subs:
        queues[sub].sort(
            key=lambda p: (
                not any(term in (p["title"] + " " + p["selftext"]).lower()
                        for term in TERMS),
                -p["created_utc"],
            )
        )
    comment_requests = 0
    while comment_requests < comment_budget and any(queues.values()):
        for sub in order:
            if comment_requests >= comment_budget:
                break
            if not queues[sub]:
                continue
            post = queues[sub].pop(0)
            comment_requests += 1
            try:
                payload = _entries(get(COMMENTS, {
                    "link_id": post["id"], "limit": MAX_COMMENTS_PER_POST,
                    "sort": "desc",
                }), "comments")
                for c in payload[:MAX_COMMENTS_PER_POST]:
                    if isinstance(c, dict) and isinstance(c.get("body"), str):
                        post["comments"].append({"body": c["body"][:12000]})
            except (OSError, ValueError, TimeoutError, json.JSONDecodeError) as exc:
                errors.append({"subreddit": sub, "post_id": post["id"],
                               "error": type(exc).__name__})
    return {
        "schema": "PREDICTION_ARCTIC_SHIFT_DISCOVERY_PULL_V1",
        "retrieved_at_utc": clock.isoformat(),
        "source_host": HOST,
        "records": list(unique.values()),
        "errors": errors,
        "requests_upper_bound": len(SUBREDDITS) + comment_budget,
        "network_read_only": True, "economic_status": "NO_PROVEN_EDGE",
    }


def write_inbox(result: dict, inbox: Path) -> Path:
    """Create immutable batch file in an existing, non-symlink inbox."""
    if not inbox.is_dir() or inbox.is_symlink():
        raise ValueError("safe existing inbox required")
    if result.get("schema") != "PREDICTION_ARCTIC_SHIFT_DISCOVERY_PULL_V1":
        raise ValueError("invalid pull")
    body = json.dumps(result["records"], sort_keys=True, ensure_ascii=True)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]
    filename = "arctic-" + digest + ".json"
    target = inbox / filename
    try:
        with target.open("x", encoding="utf-8") as handle:
            handle.write(body + "\n")
    except FileExistsError:
        if target.is_symlink() or target.read_text(encoding="utf-8") != body + "\n":
            raise
    return target


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inbox", required=True, type=Path)
    ap.add_argument("--lookback-hours", type=int, default=168)
    ap.add_argument("--limit", type=int, default=15)
    ap.add_argument("--comment-budget", type=int, default=8)
    args = ap.parse_args()
    result = collect(
        lookback_hours=args.lookback_hours, limit=args.limit,
        comment_budget=args.comment_budget,
    )
    if result["records"]:
        result["inbox_file"] = str(write_inbox(result, args.inbox))
    print(json.dumps({k: v for k, v in result.items() if k != "records"},
                     sort_keys=True))


if __name__ == "__main__":
    main()
