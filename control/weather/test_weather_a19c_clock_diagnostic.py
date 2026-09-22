#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control" / "jobs"))

import weather_a19c_clock_diagnostic as d


def test_good_clock_is_eligible():
    out = d.classify_clock_evidence({
        "clock_source": "chrony:1.2.3.4",
        "clock_offset_ms": -0.25,
        "clock_uncertainty_ms": 7.25,
        "evidence_clock_eligible": True,
    })
    assert out["clock_evidence_eligible"] is True
    assert out["reasons"] == []


def test_timedatectl_sync_without_quantitative_evidence_is_blocked():
    out = d.classify_clock_evidence({
        "clock_source": "timedatectl",
        "clock_offset_ms": None,
        "clock_uncertainty_ms": None,
        "ntp_synchronized": True,
        "evidence_clock_eligible": False,
    })
    assert out["clock_evidence_eligible"] is False
    assert "MISSING_OR_NONFINITE_CLOCK_OFFSET" in out["reasons"]
    assert "MISSING_OR_NONFINITE_CLOCK_UNCERTAINTY" in out["reasons"]


def test_uncertainty_above_gate_is_blocked():
    out = d.classify_clock_evidence({
        "clock_source": "chrony:test",
        "clock_offset_ms": 1.0,
        "clock_uncertainty_ms": 100.001,
        "evidence_clock_eligible": True,
    })
    assert out["clock_evidence_eligible"] is False
    assert "CLOCK_UNCERTAINTY_ABOVE_GATE" in out["reasons"]


def test_upstream_false_remains_blocked_even_with_numbers():
    out = d.classify_clock_evidence({
        "clock_source": "chrony:test",
        "clock_offset_ms": 0.1,
        "clock_uncertainty_ms": 1.0,
        "evidence_clock_eligible": False,
    })
    assert out["clock_evidence_eligible"] is False
    assert "UPSTREAM_CLOCK_GATE_NOT_ELIGIBLE" in out["reasons"]


if __name__ == "__main__":
    tests = [
        test_good_clock_is_eligible,
        test_timedatectl_sync_without_quantitative_evidence_is_blocked,
        test_uncertainty_above_gate_is_blocked,
        test_upstream_false_remains_blocked_even_with_numbers,
    ]
    for test in tests:
        test()
    print(f"WEATHER_A19C_CLOCK_UNIT_TESTS_PASS {len(tests)}")
