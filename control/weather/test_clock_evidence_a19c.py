#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control" / "weather"))

import clock_evidence_a19c as c


def raw(**overrides):
    base = dict(
        adjtimex_return=c.TIME_OK,
        status=c.STA_NANO,
        offset_raw=250_000,
        offset_is_nanoseconds=True,
        maxerror_us=8_000,
        esterror_us=2_000,
        precision_raw=1,
        tolerance_raw=0,
        ntp_gettime_return=c.TIME_OK,
        ntp_maxerror_us=8_000,
        ntp_esterror_us=2_000,
        ntp_time_sec=1_790_010_000,
        ntp_time_usec=123_456,
    )
    base.update(overrides)
    return c.RawKernelClock(**base)


def test_good_kernel_state_is_eligible():
    out = c.evaluate(raw())
    assert out["evidence_clock_eligible"] is True
    assert out["clock_source"] == "linux-kernel-adjtimex+ntp_gettime"
    assert out["clock_offset_ms"] == 0.25
    assert out["clock_uncertainty_ms"] == 8.0
    assert out["estimated_error_ms"] == 2.0
    assert out["read_only"] is True


def test_microsecond_offset_semantics():
    out = c.evaluate(raw(offset_raw=-750, offset_is_nanoseconds=False))
    assert out["clock_offset_ms"] == -0.75
    assert out["evidence_clock_eligible"] is True


def test_small_inter_api_tick_delta_is_allowed():
    out = c.evaluate(raw(ntp_maxerror_us=9_500))
    assert out["maxerror_api_delta_ms"] == 1.5
    assert out["api_error_fields_agree"] is True
    assert out["evidence_clock_eligible"] is True


def test_time_error_fails_closed():
    out = c.evaluate(raw(adjtimex_return=c.TIME_ERROR))
    assert out["evidence_clock_eligible"] is False


def test_unsync_fails_closed():
    out = c.evaluate(raw(status=c.STA_NANO | c.STA_UNSYNC))
    assert out["sta_unsync"] is True
    assert out["evidence_clock_eligible"] is False


def test_api_disagreement_fails_closed():
    out = c.evaluate(raw(ntp_maxerror_us=11_000))
    assert out["maxerror_api_delta_ms"] == 3.0
    assert out["api_error_fields_agree"] is False
    assert out["evidence_clock_eligible"] is False


def test_large_error_fails_closed():
    out = c.evaluate(raw(maxerror_us=100_001, ntp_maxerror_us=100_001))
    assert out["error_bounds_ok"] is False
    assert out["evidence_clock_eligible"] is False


def test_large_offset_fails_closed():
    out = c.evaluate(raw(offset_raw=100_001_000, offset_is_nanoseconds=True))
    assert out["clock_offset_ms"] == 100.001
    assert out["offset_bounds_ok"] is False
    assert out["evidence_clock_eligible"] is False


def test_negative_error_fails_closed():
    out = c.evaluate(raw(esterror_us=-1, ntp_esterror_us=-1))
    assert out["error_bounds_ok"] is False
    assert out["evidence_clock_eligible"] is False


if __name__ == "__main__":
    tests = [
        test_good_kernel_state_is_eligible,
        test_microsecond_offset_semantics,
        test_small_inter_api_tick_delta_is_allowed,
        test_time_error_fails_closed,
        test_unsync_fails_closed,
        test_api_disagreement_fails_closed,
        test_large_error_fails_closed,
        test_large_offset_fails_closed,
        test_negative_error_fails_closed,
    ]
    for test in tests:
        test()
    print(f"CLOCK_EVIDENCE_A19C_UNIT_TESTS_PASS {len(tests)}")
