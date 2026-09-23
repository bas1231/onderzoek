#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path
import sqlite3
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from public_metar_race import init_db  # noqa: E402
from analyze_public_metar_race import analyze  # noqa: E402


def add(conn, source, station, obs_ns, seen_ns, raw_suffix):
    conn.execute(
        """INSERT INTO observations(
            source,station,obs_time_ns,raw_sha256,raw_text,temperature_c,source_time_ns,
            source_status,payload_sha256,receipt_start_ns,receipt_end_ns,raw_path,inserted_at_ns
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            source, station, obs_ns, f"sha-{source}-{raw_suffix}", f"raw-{source}-{raw_suffix}", None, None,
            None, f"payload-{source}-{raw_suffix}", seen_ns - 1_000_000, seen_ns,
            f"/tmp/{source}-{raw_suffix}", seen_ns,
        ),
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "race.sqlite3"
        conn = init_db(db)
        base = datetime(2026, 9, 20, 12, tzinfo=timezone.utc)
        stations = ["KMIA", "KJFK", "KORD"]
        # 24 episodes over four UTC dates. AWC leads TWC by 20s every time.
        # tgftp trails by 5s and must not promote.
        for i in range(24):
            station = stations[i % len(stations)]
            obs_dt = base + timedelta(hours=i * 4)
            obs_ns = int(obs_dt.timestamp() * 1e9)
            twc_seen = obs_ns + 70_000_000_000
            add(conn, "twc_kalshi", station, obs_ns, twc_seen, i)
            add(conn, "awc_api", station, obs_ns, twc_seen - 20_000_000_000, i)
            add(conn, "nws_tgftp", station, obs_ns, twc_seen + 5_000_000_000, i)
        conn.commit()
        conn.close()

        report = analyze(db)
        by_source = {row["source"]: row for row in report["sources"]}
        assert report["status"] == "RESEARCH_POSITIVE_SOURCE_LEAD"
        assert by_source["awc_api"]["source_lead_gate_pass"] is True
        assert by_source["awc_api"]["matched_episodes"] == 24
        assert by_source["awc_api"]["lead_ms"]["median"] == 20000.0
        assert by_source["nws_tgftp"]["source_lead_gate_pass"] is False
        assert report["economic_conclusion"] == "NO_PROVEN_EDGE"

    print("PUBLIC_METAR_RACE_ANALYZER_TESTS_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
