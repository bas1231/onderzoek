#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control" / "weather"))

import weather_clock_diag_a19b_v2 as m


def tracking(*, system="0.000250 seconds slow of NTP time", stratum="3", delay="0.010000 seconds", dispersion="0.002000 seconds", leap="Normal") -> str:
    return f"""Reference ID    : 1.2.3.4
Stratum         : {stratum}
System time     : {system}
Last offset     : -0.000100 seconds
RMS offset      : 0.000300 seconds
Root delay      : {delay}
Root dispersion : {dispersion}
Leap status     : {leap}
"""


def assert_blocked_chrony(text: str):
    out = m.assess_chronyc_tracking(text)
    assert out["clock_evidence_eligible"] is False


def test_missing_chrony_quantitative_source_blocks():
    out = m.assess_inventory(
        chrony=None,
        ntp_synchronized=True,
        ntp_enabled=True,
        sync_marker=True,
    )
    assert out["status"] == "BLOCKED_CLOCK_EVIDENCE"
    assert out["clock_evidence_eligible"] is False
    assert out["clock_offset_ms"] is None
    assert out["clock_uncertainty_ms"] is None


def test_malformed_chrony_blocks():
    assert_blocked_chrony("garbage\n")


def test_bad_leap_blocks():
    assert_blocked_chrony(tracking(leap="Not synchronised"))


def test_bad_stratum_blocks():
    assert_blocked_chrony(tracking(stratum="16"))
    assert_blocked_chrony(tracking(stratum="unknown"))


def test_excessive_uncertainty_blocks():
    assert_blocked_chrony(
        tracking(
            system="0.150000 seconds fast of NTP time",
            delay="0.100000 seconds",
            dispersion="0.050000 seconds",
        )
    )


def test_timedatectl_yes_never_upgrades_without_numbers():
    out = m.assess_inventory(
        chrony={
            "clock_source": "chrony",
            "clock_offset_ms": None,
            "clock_uncertainty_ms": None,
            "clock_evidence_eligible": False,
            "reason": "CHRONYC_TRACKING_UNAVAILABLE",
        },
        ntp_synchronized=True,
        ntp_enabled=True,
        sync_marker=True,
    )
    assert out["status"] == "BLOCKED_CLOCK_EVIDENCE"
    assert out["clock_evidence_eligible"] is False


if __name__ == "__main__":
    tests = [
        test_missing_chrony_quantitative_source_blocks,
        test_malformed_chrony_blocks,
        test_bad_leap_blocks,
        test_bad_stratum_blocks,
        test_excessive_uncertainty_blocks,
        test_timedatectl_yes_never_upgrades_without_numbers,
    ]
    for test in tests:
        test()
    print(f"WEATHER_CLOCK_DIAG_A19B_V2_ADVERSARIAL_TESTS_PASS {len(tests)}")
