#!/usr/bin/env python3
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control" / "weather"))

import madis_omo_public_a19 as m


def test_parse_index_deduplicates_and_sorts():
    html = '''<html><body>
    <a href="20260921_1200.gz">a</a>
    <a href="junk.txt">junk</a>
    <a href="20260921_1100.gz">b</a>
    <a href="20260921_1200.gz">dup</a>
    </body></html>'''
    assert m.parse_index(html) == ["20260921_1100.gz", "20260921_1200.gz"]


def test_valid_hour_parser():
    ms = m.file_valid_hour_ms("20260921_1200.gz")
    expected = int(datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc).timestamp() * 1000)
    assert ms == expected


def test_temperature_conversions():
    assert round(m.temp_to_f(273.15, "K"), 6) == 32.0
    assert round(m.temp_to_f(0, "celsius"), 6) == 32.0
    assert round(m.temp_to_f(68, "degF"), 6) == 68.0
    assert m.temp_to_f(100, "mystery") is None


if __name__ == "__main__":
    tests = [test_parse_index_deduplicates_and_sorts, test_valid_hour_parser, test_temperature_conversions]
    for test in tests:
        test()
    print(f"MADIS_OMO_A19_TESTS_PASS {len(tests)}")
