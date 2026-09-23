#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from public_metar_race import (  # noqa: E402
    Observation,
    init_db,
    metar_ddhhmm_to_ns,
    parse_awc,
    parse_tgftp,
    parse_time_ns,
    parse_twc,
    store_observations,
)


def ns(iso: str) -> int:
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() * 1_000_000_000)


def test_parse_time_ns():
    assert parse_time_ns(1_790_000_000) == 1_790_000_000_000_000_000
    assert parse_time_ns(1_790_000_000_000) == 1_790_000_000_000_000_000
    assert parse_time_ns("2026-09-23T18:00:00Z") == ns("2026-09-23T18:00:00Z")
    assert parse_time_ns(None) is None


def test_metar_time_month_boundary():
    ref = datetime(2026, 10, 1, 0, 3, tzinfo=timezone.utc)
    actual = metar_ddhhmm_to_ns("KMIA 302353Z 09005KT 10SM CLR 28/24 A2999", ref)
    assert actual == ns("2026-09-30T23:53:00Z")


def test_awc_parser():
    body = json.dumps([{
        "icaoId": "KMIA",
        "receiptTime": "2026-09-23T18:01:02Z",
        "obsTime": 1790186400,
        "temp": 29.4,
        "rawOb": "KMIA 231800Z 10008KT 10SM FEW030 29/23 A3001",
    }]).encode()
    sha = hashlib.sha256(body).hexdigest()
    rows = parse_awc(body, 100, 200, "/tmp/awc.json", sha)
    assert len(rows) == 1
    row = rows[0]
    assert row.source == "awc_api"
    assert row.station == "KMIA"
    assert row.obs_time_ns == 1790186400 * 1_000_000_000
    assert row.temperature_c == 29.4
    assert row.source_time_ns == ns("2026-09-23T18:01:02Z")


def test_twc_parser_and_revision_storage():
    body = json.dumps({
        "fetchedAt": "2026-09-23T18:01:05Z",
        "stations": [{
            "icaoId": "KMIA",
            "observations": [{
                "icaoId": "KMIA",
                "reportTimeUTC": "2026-09-23T18:00:00Z",
                "tempC": 29.0,
                "tempF": 84.2,
                "status": "pending",
            }],
        }],
    }).encode()
    sha = hashlib.sha256(body).hexdigest()
    rows = parse_twc(body, 300, 400, "/tmp/twc.json", sha)
    assert len(rows) == 1
    assert rows[0].station == "KMIA"
    assert rows[0].source_status == "pending"
    assert rows[0].source_time_ns == ns("2026-09-23T18:01:05Z")

    with tempfile.TemporaryDirectory() as td:
        conn = init_db(Path(td) / "race.sqlite3")
        assert store_observations(conn, rows) == 1
        assert store_observations(conn, rows) == 0
        revised = Observation(**{**rows[0].__dict__, "raw_text": rows[0].raw_text + " REV"})
        assert store_observations(conn, [revised]) == 1
        count = conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
        assert count == 2
        conn.close()


def test_tgftp_parser():
    body = b"2026/09/23 18:02\nKMIA 231753Z 09006KT 10SM SCT030 29/24 A3000 RMK AO2\n"
    sha = hashlib.sha256(body).hexdigest()
    end = ns("2026-09-23T18:02:10Z")
    rows = parse_tgftp("KMIA", body, end - 10_000_000, end, "/tmp/KMIA.TXT", sha)
    assert len(rows) == 1
    assert rows[0].obs_time_ns == ns("2026-09-23T17:53:00Z")
    assert rows[0].source_time_ns == ns("2026-09-23T18:02:00Z")


def main() -> int:
    test_parse_time_ns()
    test_metar_time_month_boundary()
    test_awc_parser()
    test_twc_parser_and_revision_storage()
    test_tgftp_parser()
    print("PUBLIC_METAR_RACE_UNIT_TESTS_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
