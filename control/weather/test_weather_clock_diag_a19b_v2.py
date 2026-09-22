#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control" / "weather"))

import weather_clock_diag_a19b_v2 as m


def good_tracking() -> str:
    return """Reference ID    : 1.2.3.4
Stratum         : 3
System time     : 0.000250 seconds slow of NTP time
Last offset     : -0.000100 seconds
RMS offset      : 0.000300 seconds
Root delay      : 0.010000 seconds
Root dispersion : 0.002000 seconds
Leap status     : Normal
"""


def test_quantitative_chrony_evidence_passes():
    out = m.assess_chronyc_tracking(good_tracking())
    assert out["clock_evidence_eligible"] is True
    assert round(float(out["clock_offset_ms"]), 6) == -0.25
    assert round(float(out["clock_uncertainty_ms"]), 6) == 7.25
    assert out["reason"] == "QUANTITATIVE_CHRONY_EVIDENCE_PASS"


def test_inventory_preserves_quantitative_evidence():
    chrony = m.assess_chronyc_tracking(good_tracking())
    out = m.assess_inventory(
        chrony=chrony,
        ntp_synchronized=True,
        ntp_enabled=True,
        sync_marker=True,
    )
    assert out["status"] == "PASS_CLOCK_EVIDENCE"
    assert out["clock_evidence_eligible"] is True
    assert out["next_gate"] == "CLOCK_EVIDENCE_SATISFIED"


def test_yes_no_parser_is_strict():
    assert m._parse_yes_no("yes\n") is True
    assert m._parse_yes_no("no\n") is False
    assert m._parse_yes_no("maybe\n") is None


if __name__ == "__main__":
    tests = [
        test_quantitative_chrony_evidence_passes,
        test_inventory_preserves_quantitative_evidence,
        test_yes_no_parser_is_strict,
    ]
    for test in tests:
        test()
    print(f"WEATHER_CLOCK_DIAG_A19B_V2_UNIT_TESTS_PASS {len(tests)}")
