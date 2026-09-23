#!/usr/bin/env python3
"""Analyze prospective public-METAR source timing versus the TWC/Kalshi feed.

This analyzer is intentionally conservative. It can promote a *source-lead*
observation to RESEARCH_POSITIVE, but it can never promote an economic edge.
A market edge still requires contemporaneous market reaction and execution proof.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import statistics

HOME = Path.home()
STATE = HOME / ".local" / "state" / "prediction-research"
DB_PATH = STATE / "weather_public_race.sqlite3"
REPORTS = STATE / "weather_public_race_reports"

BASELINE = "twc_kalshi"
CANDIDATES = ("awc_api", "nws_tgftp")

# Pre-registered promotion threshold for the *source timing lane only*.
MIN_EPISODES = 20
MIN_STATIONS = 3
MIN_UTC_DATES = 2
MIN_MEDIAN_LEAD_MS = 10_000.0
MIN_POSITIVE_FRACTION = 0.75
MIN_P25_LEAD_MS = 0.0


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    frac = pos - lo
    return xs[lo] * (1.0 - frac) + xs[hi] * frac


def load_first_seen(conn: sqlite3.Connection) -> dict[tuple[str, int], dict[str, int]]:
    rows = conn.execute(
        """
        SELECT station, obs_time_ns, source, MIN(receipt_end_ns) AS first_seen_ns
        FROM observations
        WHERE source IN ('twc_kalshi','awc_api','nws_tgftp')
        GROUP BY station, obs_time_ns, source
        ORDER BY obs_time_ns, station, source
        """
    ).fetchall()
    episodes: dict[tuple[str, int], dict[str, int]] = defaultdict(dict)
    for station, obs_ns, source, seen_ns in rows:
        episodes[(str(station), int(obs_ns))][str(source)] = int(seen_ns)
    return dict(episodes)


def source_report(episodes: dict[tuple[str, int], dict[str, int]], source: str) -> dict:
    leads: list[float] = []
    stations = set()
    dates = set()
    examples = []
    for (station, obs_ns), seen in sorted(episodes.items(), key=lambda item: item[0][1]):
        if BASELINE not in seen or source not in seen:
            continue
        lead_ms = (seen[BASELINE] - seen[source]) / 1_000_000.0
        leads.append(lead_ms)
        stations.add(station)
        dates.add(datetime.fromtimestamp(obs_ns / 1e9, tz=timezone.utc).date().isoformat())
        if len(examples) < 30:
            examples.append({
                "station": station,
                "observation_time": datetime.fromtimestamp(obs_ns / 1e9, tz=timezone.utc).isoformat(),
                "candidate_first_seen": datetime.fromtimestamp(seen[source] / 1e9, tz=timezone.utc).isoformat(),
                "twc_first_seen": datetime.fromtimestamp(seen[BASELINE] / 1e9, tz=timezone.utc).isoformat(),
                "lead_ms": round(lead_ms, 3),
            })

    n = len(leads)
    median = statistics.median(leads) if leads else None
    p25 = percentile(leads, 0.25)
    p75 = percentile(leads, 0.75)
    positive_fraction = (sum(1 for x in leads if x > 0) / n) if n else None
    promotion = bool(
        n >= MIN_EPISODES
        and len(stations) >= MIN_STATIONS
        and len(dates) >= MIN_UTC_DATES
        and median is not None and median >= MIN_MEDIAN_LEAD_MS
        and positive_fraction is not None and positive_fraction >= MIN_POSITIVE_FRACTION
        and p25 is not None and p25 > MIN_P25_LEAD_MS
    )
    return {
        "source": source,
        "baseline": BASELINE,
        "matched_episodes": n,
        "station_count": len(stations),
        "stations": sorted(stations),
        "utc_date_count": len(dates),
        "utc_dates": sorted(dates),
        "lead_ms_semantics": "positive means candidate source was observed locally before TWC/Kalshi feed",
        "lead_ms": {
            "min": min(leads) if leads else None,
            "p25": p25,
            "median": median,
            "mean": statistics.fmean(leads) if leads else None,
            "p75": p75,
            "max": max(leads) if leads else None,
        },
        "positive_lead_fraction": positive_fraction,
        "lead_ge_5s_fraction": (sum(1 for x in leads if x >= 5_000) / n) if n else None,
        "lead_ge_15s_fraction": (sum(1 for x in leads if x >= 15_000) / n) if n else None,
        "lead_ge_30s_fraction": (sum(1 for x in leads if x >= 30_000) / n) if n else None,
        "source_lead_gate_pass": promotion,
        "source_lead_status": "RESEARCH_POSITIVE" if promotion else "INSUFFICIENT_OR_NEGATIVE_SOURCE_LEAD_EVIDENCE",
        "examples": examples,
    }


def analyze(db_path: Path) -> dict:
    if not db_path.is_file():
        return {
            "status": "BLOCKED_DB_MISSING",
            "db": str(db_path),
            "economic_conclusion": "NO_PROVEN_EDGE",
        }
    conn = sqlite3.connect(db_path)
    try:
        episodes = load_first_seen(conn)
        source_reports = [source_report(episodes, source) for source in CANDIDATES]
        fetch_errors = conn.execute("SELECT COUNT(*) FROM fetches WHERE error IS NOT NULL").fetchone()[0]
        fetch_total = conn.execute("SELECT COUNT(*) FROM fetches").fetchone()[0]
        obs_total = conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
    finally:
        conn.close()

    promoted = [row["source"] for row in source_reports if row["source_lead_gate_pass"]]
    return {
        "task": "WEATHER-PUBLIC-METAR-SOURCE-RACE-ANALYSIS",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "RESEARCH_POSITIVE_SOURCE_LEAD" if promoted else "NO_SOURCE_LEAD_PROMOTED",
        "db": str(db_path),
        "observation_revision_rows": obs_total,
        "fetch_count": fetch_total,
        "fetch_error_count": fetch_errors,
        "preregistered_source_lead_gate": {
            "min_matched_episodes": MIN_EPISODES,
            "min_stations": MIN_STATIONS,
            "min_utc_dates": MIN_UTC_DATES,
            "min_median_lead_ms": MIN_MEDIAN_LEAD_MS,
            "min_positive_fraction": MIN_POSITIVE_FRACTION,
            "p25_lead_ms_must_be_gt": MIN_P25_LEAD_MS,
        },
        "promoted_sources": promoted,
        "sources": source_reports,
        "interpretation_guard": (
            "Passing this gate proves only a repeatable collector-level source lead versus the public TWC/Kalshi feed. "
            "It does not prove contract semantics, market reaction, executable prices, fills, or profit."
        ),
        "next_gate": (
            "LINK_PROMOTED_SOURCE_EPISODES_TO_POINT_IN_TIME_KALSHI_REACTION"
            if promoted else "CONTINUE_PROSPECTIVE_COLLECTION_OR_KILL_SOURCE_LANE"
        ),
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
        "economic_conclusion": "NO_PROVEN_EDGE",
    }


def write_report(report: dict) -> Path:
    REPORTS.mkdir(parents=True, exist_ok=True)
    body = json.dumps(report, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(body).hexdigest()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    path = REPORTS / f"public-metar-race-analysis-{stamp}-{digest[:12]}.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    latest = REPORTS / "latest.json"
    latest.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(DB_PATH))
    args = ap.parse_args()
    report = analyze(Path(args.db).expanduser())
    path = write_report(report)
    report["report"] = str(path)
    print(json.dumps(report, indent=2, sort_keys=True))
    # Missing data is not a software error; only missing/corrupt DB is blocked.
    return 2 if report.get("status") == "BLOCKED_DB_MISSING" else 0


if __name__ == "__main__":
    raise SystemExit(main())
