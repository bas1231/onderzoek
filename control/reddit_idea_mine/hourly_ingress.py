"""Bounded, fail-soft Reddit idea ingress for canonical hourly Recon routing.

External source access only occurs when this entrypoint is explicitly enabled.
It reuses canonical Recon discovery rather than building its own promotion path.
Remote discussion text is always untrusted evidence, never an instruction.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from control.reddit_idea_mine import arctic_shift_source, ingest, recon_handoff, freshness

def inject(routing: dict, *, enabled: bool = False, fetch=None,
           now: datetime | None = None) -> dict:
    if not isinstance(routing, dict):
        raise ValueError("routing must be an object")
    base = {
        "schema": "PREDICTION_REDDIT_HOURLY_INGRESS_V1",
        "enabled": bool(enabled), "status": "DISABLED",
        "posts_received": 0, "leads_accepted": 0,
        "evidence_added": 0, "errors": [],
        "economic_conclusion": "NO_PROVEN_EDGE",
        "candidate_created": False, "live_trading": False,
        "paid_actions": False, "wallet_actions": False,
    }
    if not enabled:
        return base
    try:
        pulled = arctic_shift_source.collect(
            fetch=fetch, now=now, lookback_hours=168,
            limit=12, comment_budget=4,
        )
        batch = ingest.ingest(pulled["records"])
        age_report = freshness.report(
            batch,
            observed_at=datetime.fromisoformat(pulled["retrieved_at_utc"]),
            max_age_minutes=30,
        )
        route = recon_handoff.to_recon_routing(batch)
        incoming = route["recon_scout"]["evidence"]
        current = routing.setdefault("recon_scout", {})
        if not isinstance(current, dict):
            raise ValueError("invalid existing recon role")
        existing = current.setdefault("evidence", [])
        if not isinstance(existing, list):
            raise ValueError("invalid existing evidence list")
        keys = {(x.get("source_id"), x.get("document_sha256"))
                for x in existing if isinstance(x, dict)}
        added = 0
        for item in incoming:
            key = (item["source_id"], item["document_sha256"])
            if key not in keys:
                existing.append(item)
                keys.add(key)
                added += 1
        base.update({
            "status": (
                ("PARTIAL" if pulled["records"] else "SOURCE_FAILURE")
                if pulled["errors"] else
                ("SUCCESS" if batch["counts"]["accepted_unique"] > 0 else "EMPTY")
            ),
            "posts_received": len(pulled["records"]),
            "leads_accepted": batch["counts"]["accepted_unique"],
            "evidence_added": added,
            "errors": pulled["errors"][:20],
            "observed_at_utc": pulled["retrieved_at_utc"],
            "provider": "arctic_shift",
            "fresh_under_30_minutes": age_report["fresh_under_horizon"],
            "median_post_age_minutes": age_report["median_age_minutes"],
            "future_timestamp_rejected": age_report["future_timestamp_rejected"],
            "timeliness_proven": False,
        })
    except (ValueError, TypeError, OSError, KeyError, OverflowError,
            json.JSONDecodeError) as exc:
        base.update({"status": "SOURCE_FAILURE",
                     "errors": [{"error": type(exc).__name__}]})
    return base


def persist_receipt(root: Path, run_id: str, receipt: dict) -> Path:
    """Persist one per-cycle receipt; no new service, no candidate writes."""
    if not run_id or len(run_id) > 120 or not all(
        c.isalnum() or c in "-_+." for c in run_id
    ):
        raise ValueError("invalid run id")
    output = root / "knowledge/runs/reddit_idea_mine"
    output.mkdir(parents=True, exist_ok=True)
    path = output / (run_id + "-hourly-source.json")
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    return path
