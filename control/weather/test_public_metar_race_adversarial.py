#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from public_metar_race import (  # noqa: E402
    metar_ddhhmm_to_ns,
    normalize_station,
    parse_awc,
    parse_tgftp,
    parse_time_ns,
    parse_twc,
)


def ns(text: str) -> int:
    return int(datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp() * 1e9)


def main() -> int:
    # Malformed or ambiguous station IDs fail closed.
    assert normalize_station("KMIA") == "KMIA"
    assert normalize_station("KMI") is None
    assert normalize_station("../../") is None
    assert normalize_station("") is None

    # Bad/empty AWC payloads cannot manufacture observations.
    assert parse_awc(b"{}", 1, 2, "/tmp/a", "x") == []
    bad_awc = json.dumps([{"icaoId": "KMIA", "obsTime": None, "rawOb": "KMIA 231800Z TEST"}]).encode()
    assert parse_awc(bad_awc, 1, 2, "/tmp/a", hashlib.sha256(bad_awc).hexdigest()) == []

    # AWC source receipt time is metadata only; local receipt_end remains the
    # timing basis. An impossible future receipt timestamp must not alter it.
    awc = json.dumps([{
        "icaoId": "KMIA", "obsTime": 1790186400,
        "receiptTime": "2099-01-01T00:00:00Z",
        "rawOb": "KMIA 231800Z 00000KT 10SM CLR 30/22 A3000",
    }]).encode()
    rows = parse_awc(awc, 100, 200, "/tmp/a", hashlib.sha256(awc).hexdigest())
    assert len(rows) == 1
    assert rows[0].receipt_end_ns == 200
    assert rows[0].source_time_ns != rows[0].receipt_end_ns

    # TWC rows without an observation timestamp are not accepted as episodes.
    twc = json.dumps({"stations": [{"observations": [{"icaoId": "KMIA", "tempC": 30}]}]}).encode()
    assert parse_twc(twc, 1, 2, "/tmp/t", hashlib.sha256(twc).hexdigest()) == []

    # Invalid/stale DDHHMMZ date mappings are rejected instead of silently
    # mapping to an arbitrary month.
    ref = datetime(2026, 9, 23, 18, tzinfo=timezone.utc)
    assert metar_ddhhmm_to_ns("KMIA 992500Z TEST", ref) is None

    # tgftp header alone is not treated as observation time: missing METAR time
    # means no race episode.
    tg = b"2026/09/23 18:02\nKMIA AUTO TEST WITHOUT METAR TIME\n"
    assert parse_tgftp("KMIA", tg, ns("2026-09-23T18:02:00Z") - 1, ns("2026-09-23T18:02:00Z"), "/tmp/tg", "x") == []

    # Timestamp parser rejects nonsensical values rather than fabricating time.
    assert parse_time_ns(0) is None
    assert parse_time_ns("not-a-time") is None

    print("PUBLIC_METAR_RACE_ADVERSARIAL_TESTS_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
