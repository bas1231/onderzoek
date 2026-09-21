#!/usr/bin/env python3
from __future__ import annotations

import ctypes
import errno
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control" / "weather"))

import clock_evidence_a19c as c


class FakeLib:
    def __init__(self, *, fail_adj=False, fail_ntp=False, status=None):
        self.fail_adj = fail_adj
        self.fail_ntp = fail_ntp
        self.status = c.STA_NANO if status is None else status
        self.seen_modes = None

    def adjtimex(self, arg):
        tx = ctypes.cast(arg, ctypes.POINTER(c.Timex)).contents
        self.seen_modes = int(tx.modes)
        if self.fail_adj:
            ctypes.set_errno(errno.EPERM)
            return -1
        tx.status = self.status
        tx.offset = 100_000
        tx.maxerror = 5_000
        tx.esterror = 2_000
        return c.TIME_OK

    def ntp_gettime(self, arg):
        ntv = ctypes.cast(arg, ctypes.POINTER(c.NtpTimeval)).contents
        if self.fail_ntp:
            ctypes.set_errno(errno.EIO)
            return -1
        ntv.maxerror = 5_000
        ntv.esterror = 2_000
        ntv.time.tv_sec = 1_790_010_000
        ntv.time.tv_usec = 123_456
        return c.TIME_OK


def test_read_path_is_modes_zero_only():
    lib = FakeLib()
    raw = c.read_kernel_clock(lib)
    assert lib.seen_modes == 0
    assert raw.maxerror_us == 5_000
    assert raw.ntp_maxerror_us == 5_000


def test_adjtimex_failure_is_not_silently_accepted():
    try:
        c.read_kernel_clock(FakeLib(fail_adj=True))
    except OSError as exc:
        assert exc.errno == errno.EPERM
    else:
        raise AssertionError("adjtimex failure was silently accepted")


def test_ntp_gettime_failure_is_not_silently_accepted():
    try:
        c.read_kernel_clock(FakeLib(fail_ntp=True))
    except OSError as exc:
        assert exc.errno == errno.EIO
    else:
        raise AssertionError("ntp_gettime failure was silently accepted")


def test_clockerr_fails_closed():
    raw = c.read_kernel_clock(FakeLib(status=c.STA_NANO | c.STA_CLOCKERR))
    out = c.evaluate(raw)
    assert out["sta_clockerr"] is True
    assert out["evidence_clock_eligible"] is False


def test_both_time_apis_must_be_synchronized():
    good = c.RawKernelClock(
        adjtimex_return=c.TIME_OK,
        status=c.STA_NANO,
        offset_raw=0,
        offset_is_nanoseconds=True,
        maxerror_us=1_000,
        esterror_us=1_000,
        precision_raw=1,
        tolerance_raw=0,
        ntp_gettime_return=c.TIME_ERROR,
        ntp_maxerror_us=1_000,
        ntp_esterror_us=1_000,
        ntp_time_sec=1,
        ntp_time_usec=0,
    )
    assert c.evaluate(good)["evidence_clock_eligible"] is False


if __name__ == "__main__":
    tests = [
        test_read_path_is_modes_zero_only,
        test_adjtimex_failure_is_not_silently_accepted,
        test_ntp_gettime_failure_is_not_silently_accepted,
        test_clockerr_fails_closed,
        test_both_time_apis_must_be_synchronized,
    ]
    for test in tests:
        test()
    print(f"CLOCK_EVIDENCE_A19C_ADVERSARIAL_TESTS_PASS {len(tests)}")
