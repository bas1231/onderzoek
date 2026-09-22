#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control" / "jobs"))

import weather_a19c_clock_diagnostic as d


def assert_blocked(clock):
    out = d.classify_clock_evidence(clock)
    assert out["clock_evidence_eligible"] is False
    return out


def test_missing_source_blocks():
    out = assert_blocked({
        "clock_source": None,
        "clock_offset_ms": 0.0,
        "clock_uncertainty_ms": 1.0,
        "evidence_clock_eligible": True,
    })
    assert "MISSING_CLOCK_SOURCE" in out["reasons"]


def test_nan_offset_blocks():
    out = assert_blocked({
        "clock_source": "chrony:test",
        "clock_offset_ms": math.nan,
        "clock_uncertainty_ms": 1.0,
        "evidence_clock_eligible": True,
    })
    assert "MISSING_OR_NONFINITE_CLOCK_OFFSET" in out["reasons"]


def test_infinite_uncertainty_blocks():
    out = assert_blocked({
        "clock_source": "chrony:test",
        "clock_offset_ms": 0.0,
        "clock_uncertainty_ms": math.inf,
        "evidence_clock_eligible": True,
    })
    assert "MISSING_OR_NONFINITE_CLOCK_UNCERTAINTY" in out["reasons"]


def test_negative_uncertainty_blocks():
    out = assert_blocked({
        "clock_source": "chrony:test",
        "clock_offset_ms": 0.0,
        "clock_uncertainty_ms": -0.001,
        "evidence_clock_eligible": True,
    })
    assert "NEGATIVE_CLOCK_UNCERTAINTY" in out["reasons"]


def test_boolean_numbers_do_not_pass():
    out = assert_blocked({
        "clock_source": "chrony:test",
        "clock_offset_ms": True,
        "clock_uncertainty_ms": False,
        "evidence_clock_eligible": True,
    })
    assert "MISSING_OR_NONFINITE_CLOCK_OFFSET" in out["reasons"]
    assert "MISSING_OR_NONFINITE_CLOCK_UNCERTAINTY" in out["reasons"]


if __name__ == "__main__":
    tests = [
        test_missing_source_blocks,
        test_nan_offset_blocks,
        test_infinite_uncertainty_blocks,
        test_negative_uncertainty_blocks,
        test_boolean_numbers_do_not_pass,
    ]
    for test in tests:
        test()
    print(f"WEATHER_A19C_CLOCK_ADVERSARIAL_TESTS_PASS {len(tests)}")
