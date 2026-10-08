"""Pure, offline freshness report for a bounded Reddit discovery batch."""
from __future__ import annotations
from datetime import datetime, timezone
from statistics import median

def report(batch: dict, observed_at: datetime | None = None, max_age_minutes: int = 30) -> dict:
    if batch.get("schema") != "PREDICTION_REDDIT_DISCOVERY_BATCH_V1":
        raise ValueError("invalid batch")
    if not 1 <= max_age_minutes <= 1440:
        raise ValueError("invalid freshness horizon")
    now = observed_at or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("timezone required")
    ages = []
    future = 0
    fresh = 0
    for lead in batch.get("leads", []):
        published = datetime.fromisoformat(lead["created_at_utc"].replace("Z", "+00:00"))
        age = (now - published).total_seconds() / 60
        if age < -2:
            future += 1
        else:
            age = max(0, age)
            ages.append(age)
            if age <= max_age_minutes:
                fresh += 1
    return {
        "schema": "PREDICTION_REDDIT_FRESHNESS_V1",
        "observed_at_utc": now.astimezone(timezone.utc).isoformat(),
        "fresh_under_horizon": fresh,
        "usable_leads": len(ages),
        "future_timestamp_rejected": future,
        "median_age_minutes": round(median(ages), 3) if ages else None,
        "minimum_age_minutes": round(min(ages), 3) if ages else None,
        "maximum_age_minutes": round(max(ages), 3) if ages else None,
        "timeliness_proven": False,
        "note": "Post age in an supplied batch is NOT source-ingestion latency; compare against authoritative independent arrival observations.",
    }
