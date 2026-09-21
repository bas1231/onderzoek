#!/usr/bin/env python3
"""Read-only progress/health report for prospective E401 evidence collection.

This does not infer economic edge. It summarizes what has actually been archived
and keeps the preregistered sample-size/city gate separate from synchronized
coverage, which requires signal-to-market linkage before it can pass.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path

STATE = Path.home() / ".local" / "state" / "prediction-research"
MANIFESTS = STATE / "e401_prospective_manifests"
KWI_MANIFESTS = STATE / "kalshi_weather_index_manifests"
TWC_MANIFESTS = STATE / "twc_hourly_manifests"

MIN_EVENTS = 30
MIN_CITIES = 2
MIN_SYNC_COVERAGE = 0.95


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def read_ndjson_health(path: Path) -> dict:
    out = {
        "exists": path.is_file(),
        "ws_connected": False,
        "market_state_events": 0,
        "capture_gaps": 0,
        "capture_errors": 0,
        "run_start": False,
        "run_end": False,
    }
    if not path.is_file():
        return out
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(raw)
        except Exception:
            continue
        kind = row.get("kind")
        if kind == "ws_connected":
            out["ws_connected"] = True
        elif kind == "market_state":
            out["market_state_events"] += 1
        elif kind == "capture_gap":
            out["capture_gaps"] += 1
        elif kind == "capture_error":
            out["capture_errors"] += 1
        elif kind == "run_start":
            out["run_start"] = True
        elif kind == "run_end":
            out["run_end"] = True
    return out


discovery_files = sorted(MANIFESTS.glob("discovery-*.json")) if MANIFESTS.is_dir() else []
cycle_files = sorted(MANIFESTS.glob("cycle-*.json")) if MANIFESTS.is_dir() else []
error_files = sorted(MANIFESTS.glob("error-*.json")) if MANIFESTS.is_dir() else []

unique_events = set()
events_by_city = defaultdict(set)
event_first_seen = {}
discovery_errors = 0

for path in discovery_files:
    obj = read_json(path)
    if not isinstance(obj, dict):
        continue
    retrieved_at = obj.get("retrieved_at")
    for series_row in obj.get("series") or []:
        city = series_row.get("city")
        if series_row.get("error"):
            discovery_errors += 1
        for event in series_row.get("events") or []:
            ticker = event.get("event_ticker")
            if not city or not ticker:
                continue
            key = (city, ticker)
            unique_events.add(key)
            events_by_city[city].add(ticker)
            event_first_seen.setdefault(f"{city}:{ticker}", retrieved_at)

clean_cycles = 0
capture_cycles = 0
capture_logs_checked = 0
capture_logs_clean = 0
capture_gap_total = 0
capture_error_total = 0
market_state_total = 0
missing_capture_logs = 0

for path in cycle_files:
    obj = read_json(path)
    if not isinstance(obj, dict):
        continue
    capture = obj.get("capture")
    if not isinstance(capture, dict):
        continue
    capture_cycles += 1
    summary = capture.get("summary") or {}
    log_value = summary.get("log") if isinstance(summary, dict) else None
    if not log_value:
        missing_capture_logs += 1
        continue
    log_path = Path(log_value)
    health = read_ndjson_health(log_path)
    capture_logs_checked += 1
    capture_gap_total += health["capture_gaps"]
    capture_error_total += health["capture_errors"]
    market_state_total += health["market_state_events"]
    clean = (
        capture.get("returncode") == 0
        and health["exists"]
        and health["ws_connected"]
        and health["market_state_events"] > 0
        and health["capture_gaps"] == 0
        and health["capture_errors"] == 0
        and health["run_start"]
        and health["run_end"]
    )
    if clean:
        clean_cycles += 1
        capture_logs_clean += 1

observed_city_count = len([city for city, events in events_by_city.items() if events])
unique_event_count = len(unique_events)
market_capture_clean_rate = (
    clean_cycles / capture_cycles if capture_cycles else None
)

kwi_manifest_count = len(list(KWI_MANIFESTS.glob("kwi-*.json"))) if KWI_MANIFESTS.is_dir() else 0
twc_manifest_count = len(list(TWC_MANIFESTS.glob("*.json"))) if TWC_MANIFESTS.is_dir() else 0

sample_gate_pass = unique_event_count >= MIN_EVENTS and observed_city_count >= MIN_CITIES

report = {
    "task": "EDGE-HUNTER-KWI-PROSPECTIVE-HEALTH-E401A16",
    "retrieved_at": datetime.now(timezone.utc).isoformat(),
    "preregistered_gate": {
        "minimum_unique_primary_events": MIN_EVENTS,
        "minimum_cities": MIN_CITIES,
        "minimum_synchronized_coverage": MIN_SYNC_COVERAGE,
    },
    "observed": {
        "unique_event_count": unique_event_count,
        "observed_city_count": observed_city_count,
        "events_by_city": {city: len(events) for city, events in sorted(events_by_city.items())},
        "discovery_manifest_count": len(discovery_files),
        "cycle_manifest_count": len(cycle_files),
        "error_manifest_count": len(error_files),
        "discovery_error_count": discovery_errors,
        "capture_cycles": capture_cycles,
        "clean_capture_cycles": clean_cycles,
        "market_capture_clean_rate": market_capture_clean_rate,
        "capture_logs_checked": capture_logs_checked,
        "capture_logs_clean": capture_logs_clean,
        "missing_capture_logs": missing_capture_logs,
        "capture_gap_total": capture_gap_total,
        "capture_error_total": capture_error_total,
        "market_state_total": market_state_total,
        "kwi_manifest_count": kwi_manifest_count,
        "twc_manifest_count": twc_manifest_count,
    },
    "sample_size_city_gate_pass": sample_gate_pass,
    "synchronized_coverage_gate": {
        "status": "NOT_YET_EVALUATED",
        "reason": "Requires primary decision-eligible KWI signal events linked point-in-time to contemporaneous market coverage; raw capture health alone is not the preregistered synchronized-coverage denominator.",
    },
    "overall_e401_gate": "COLLECTING" if not sample_gate_pass else "AWAIT_SYNC_COVERAGE_ANALYSIS",
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
}

print(json.dumps(report, indent=2, sort_keys=True))
