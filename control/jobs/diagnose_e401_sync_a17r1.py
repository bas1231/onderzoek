#!/usr/bin/env python3
"""Read-only diagnostic for E401 A17 unproven synchronization results."""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path

STATE = Path.home() / ".local" / "state" / "prediction-research"
REPORT = STATE / "e401_reaction_reports" / "e401-a17-latest.json"


def normalize_reason(reason: str) -> str:
    text = str(reason)
    if ":" in text and text.startswith("KX"):
        return text.split(":", 1)[1]
    return text


if not REPORT.is_file():
    print(json.dumps({
        "task": "EDGE-HUNTER-KWI-SYNC-DIAG-E401A17R1",
        "status": "BLOCKED_REPORT_MISSING",
        "report": str(REPORT),
        "economic_conclusion": "NO_PROVEN_EDGE",
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
    }, indent=2, sort_keys=True))
    raise SystemExit(10)

obj = json.loads(REPORT.read_text(encoding="utf-8"))
reason_counts = Counter()
raw_reason_counts = Counter()
city_status = defaultdict(Counter)
city_reasons = defaultdict(Counter)
event_examples = []

for result in obj.get("results") or []:
    event = result.get("kwi_event") or {}
    city = str(event.get("city") or "unknown").lower()
    status = str(result.get("status") or "UNKNOWN")
    city_status[city][status] += 1
    reasons = result.get("reasons") or []
    for reason in reasons:
        raw_reason_counts[str(reason)] += 1
        normalized = normalize_reason(str(reason))
        reason_counts[normalized] += 1
        city_reasons[city][normalized] += 1
    if len(event_examples) < 12:
        event_examples.append({
            "city": city,
            "kwi_t": event.get("kwi_t"),
            "available_at_ms": event.get("available_at_ms"),
            "event_ticker": result.get("event_ticker"),
            "bucket_count": result.get("bucket_count"),
            "capture_log_count": result.get("capture_log_count"),
            "status": status,
            "reasons": reasons[:8],
        })

out = {
    "task": "EDGE-HUNTER-KWI-SYNC-DIAG-E401A17R1",
    "status": "PASS",
    "report": str(REPORT),
    "primary_events_total": obj.get("primary_events_total", 0),
    "pending_primary_events_total": obj.get("pending_primary_events_total", 0),
    "evaluable_primary_events": obj.get("evaluable_primary_events", 0),
    "valid_synchronized_capture_fraction": obj.get("valid_synchronized_capture_fraction", 0.0),
    "reason_counts": dict(reason_counts.most_common()),
    "raw_reason_counts_top20": dict(raw_reason_counts.most_common(20)),
    "city_status_counts": {city: dict(counts) for city, counts in sorted(city_status.items())},
    "city_reason_counts": {city: dict(counts.most_common()) for city, counts in sorted(city_reasons.items())},
    "event_examples": event_examples,
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
}
print(json.dumps(out, indent=2, sort_keys=True))
