"""Convert supplied archive records into Prediction Reddit discussion input.

No network I/O: records must be delivered by a separately approved source.
The caller asserts provenance; this module does not grant usage rights.
"""
from __future__ import annotations
import json
from pathlib import Path

from control.reddit_idea_mine.ingest import ingest

def convert(records: list[dict], provenance: str = "licensed_archive") -> dict:
    if provenance not in {"licensed_archive", "authorized_export", "manual_submission", "test_fixture"}:
        raise ValueError("unrecognized provenance")
    if not isinstance(records, list) or len(records) > 500:
        raise ValueError("max 500 archive records")
    normalized = []
    for raw in records:
        if not isinstance(raw, dict):
            normalized.append(raw)
            continue
        permalink = raw.get("permalink") or raw.get("url") or ""
        if isinstance(permalink, str) and permalink.startswith("/r/"):
            permalink = "https://www.reddit.com" + permalink
        normalized.append({
            "id": raw.get("id"), "subreddit": raw.get("subreddit"),
            "url": permalink, "title": raw.get("title"),
            "selftext": raw.get("selftext") or raw.get("body") or "",
            "created_utc": raw.get("created_utc"),
            "comments": raw.get("comments") or [],
            "source": provenance,
        })
    return ingest(normalized)

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--provenance", default="licensed_archive")
    args=parser.parse_args()
    batch=convert(json.loads(args.input.read_text(encoding="utf-8")),args.provenance)
    args.output.write_text(json.dumps(batch,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(batch["counts"],sort_keys=True))

if __name__ == "__main__":
    main()
