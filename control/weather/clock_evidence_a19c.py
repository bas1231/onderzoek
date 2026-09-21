#!/usr/bin/env python3
"""A19C: read-only local kernel clock-evidence probe.

This module never adjusts the system clock. It calls Linux adjtimex() with
modes=0 and ntp_gettime() to read kernel time-discipline state. Evidence is
eligible only when both APIs agree that the clock is synchronized and the
reported error and offset stay within conservative local thresholds.

This is an evidence-quality gate for latency research, not a claim that the
kernel values equal an external ground-truth UTC comparison.
"""
from __future__ import annotations

import ctypes
import ctypes.util
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
import platform

MAX_ERROR_MS = 100.0
MAX_EST_ERROR_MS = 100.0
MAX_ABS_OFFSET_MS = 100.0
MAX_API_ERROR_DELTA_MS = 2.0

TIME_OK = 0
TIME_INS = 1
TIME_DEL = 2
TIME_OOP = 3
TIME_WAIT = 4
TIME_ERROR = 5

STA_UNSYNC = 0x0040
STA_CLOCKERR = 0x1000
STA_NANO = 0x2000


class Timeval(ctypes.Structure):
    _fields_ = [("tv_sec", ctypes.c_long), ("tv_usec", ctypes.c_long)]


class Timex(ctypes.Structure):
    _fields_ = [
        ("modes", ctypes.c_uint),
        ("offset", ctypes.c_long),
        ("freq", ctypes.c_long),
        ("maxerror", ctypes.c_long),
        ("esterror", ctypes.c_long),
        ("status", ctypes.c_int),
        ("constant", ctypes.c_long),
        ("precision", ctypes.c_long),
        ("tolerance", ctypes.c_long),
        ("time", Timeval),
        ("tick", ctypes.c_long),
        ("ppsfreq", ctypes.c_long),
        ("jitter", ctypes.c_long),
        ("shift", ctypes.c_int),
        ("stabil", ctypes.c_long),
        ("jitcnt", ctypes.c_long),
        ("calcnt", ctypes.c_long),
        ("errcnt", ctypes.c_long),
        ("stbcnt", ctypes.c_long),
        ("tai", ctypes.c_int),
        ("_padding", ctypes.c_int * 11),
    ]


class NtpTimeval(ctypes.Structure):
    _fields_ = [
        ("time", Timeval),
        ("maxerror", ctypes.c_long),
        ("esterror", ctypes.c_long),
        ("tai", ctypes.c_long),
        ("_reserved", ctypes.c_long * 4),
    ]


@dataclass(frozen=True)
class RawKernelClock:
    adjtimex_return: int
    status: int
    offset_raw: int
    offset_is_nanoseconds: bool
    maxerror_us: int
    esterror_us: int
    precision_raw: int
    tolerance_raw: int
    ntp_gettime_return: int
    ntp_maxerror_us: int
    ntp_esterror_us: int
    ntp_time_sec: int
    ntp_time_usec: int


def _libc() -> ctypes.CDLL:
    name = ctypes.util.find_library("c") or "libc.so.6"
    lib = ctypes.CDLL(name, use_errno=True)
    lib.adjtimex.argtypes = [ctypes.POINTER(Timex)]
    lib.adjtimex.restype = ctypes.c_int
    lib.ntp_gettime.argtypes = [ctypes.POINTER(NtpTimeval)]
    lib.ntp_gettime.restype = ctypes.c_int
    return lib


def read_kernel_clock(lib: ctypes.CDLL | None = None) -> RawKernelClock:
    lib = lib or _libc()
    tx = Timex()
    tx.modes = 0
    ctypes.set_errno(0)
    rc_adj = int(lib.adjtimex(ctypes.byref(tx)))
    if rc_adj < 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err), "adjtimex(modes=0)")

    ntv = NtpTimeval()
    ctypes.set_errno(0)
    rc_ntp = int(lib.ntp_gettime(ctypes.byref(ntv)))
    if rc_ntp < 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err), "ntp_gettime")

    return RawKernelClock(
        adjtimex_return=rc_adj,
        status=int(tx.status),
        offset_raw=int(tx.offset),
        offset_is_nanoseconds=bool(tx.status & STA_NANO),
        maxerror_us=int(tx.maxerror),
        esterror_us=int(tx.esterror),
        precision_raw=int(tx.precision),
        tolerance_raw=int(tx.tolerance),
        ntp_gettime_return=rc_ntp,
        ntp_maxerror_us=int(ntv.maxerror),
        ntp_esterror_us=int(ntv.esterror),
        ntp_time_sec=int(ntv.time.tv_sec),
        ntp_time_usec=int(ntv.time.tv_usec),
    )


def evaluate(raw: RawKernelClock) -> dict:
    offset_ms = raw.offset_raw / (1_000_000.0 if raw.offset_is_nanoseconds else 1000.0)
    maxerror_ms = raw.maxerror_us / 1000.0
    esterror_ms = raw.esterror_us / 1000.0
    ntp_maxerror_ms = raw.ntp_maxerror_us / 1000.0
    ntp_esterror_ms = raw.ntp_esterror_us / 1000.0

    unsync_flag = bool(raw.status & STA_UNSYNC)
    clockerr_flag = bool(raw.status & STA_CLOCKERR)
    adj_state_ok = raw.adjtimex_return != TIME_ERROR
    ntp_state_ok = raw.ntp_gettime_return != TIME_ERROR
    errors_nonnegative = all(
        value >= 0
        for value in (
            raw.maxerror_us,
            raw.esterror_us,
            raw.ntp_maxerror_us,
            raw.ntp_esterror_us,
        )
    )
    maxerror_delta_ms = abs(maxerror_ms - ntp_maxerror_ms)
    esterror_delta_ms = abs(esterror_ms - ntp_esterror_ms)
    api_agree = bool(
        maxerror_delta_ms <= MAX_API_ERROR_DELTA_MS
        and esterror_delta_ms <= MAX_API_ERROR_DELTA_MS
    )
    error_bounds_ok = bool(
        errors_nonnegative
        and maxerror_ms <= MAX_ERROR_MS
        and esterror_ms <= MAX_EST_ERROR_MS
        and ntp_maxerror_ms <= MAX_ERROR_MS
        and ntp_esterror_ms <= MAX_EST_ERROR_MS
    )
    offset_bounds_ok = abs(offset_ms) <= MAX_ABS_OFFSET_MS
    eligible = bool(
        adj_state_ok
        and ntp_state_ok
        and not unsync_flag
        and not clockerr_flag
        and api_agree
        and error_bounds_ok
        and offset_bounds_ok
    )

    return {
        "clock_source": "linux-kernel-adjtimex+ntp_gettime",
        "clock_offset_ms": offset_ms,
        "clock_uncertainty_ms": max(maxerror_ms, ntp_maxerror_ms),
        "clock_uncertainty_semantics": "kernel maxerror; read-only local discipline evidence, not an external UTC round-trip measurement",
        "estimated_error_ms": max(esterror_ms, ntp_esterror_ms),
        "maxerror_ms": maxerror_ms,
        "ntp_maxerror_ms": ntp_maxerror_ms,
        "esterror_ms": esterror_ms,
        "ntp_esterror_ms": ntp_esterror_ms,
        "maxerror_api_delta_ms": maxerror_delta_ms,
        "esterror_api_delta_ms": esterror_delta_ms,
        "kernel_status": raw.status,
        "sta_unsync": unsync_flag,
        "sta_clockerr": clockerr_flag,
        "adjtimex_return": raw.adjtimex_return,
        "ntp_gettime_return": raw.ntp_gettime_return,
        "api_error_fields_agree": api_agree,
        "error_bounds_ok": error_bounds_ok,
        "offset_bounds_ok": offset_bounds_ok,
        "evidence_clock_eligible": eligible,
        "read_only": True,
        "thresholds": {
            "max_error_ms": MAX_ERROR_MS,
            "max_est_error_ms": MAX_EST_ERROR_MS,
            "max_abs_offset_ms": MAX_ABS_OFFSET_MS,
            "max_api_error_delta_ms": MAX_API_ERROR_DELTA_MS,
        },
    }


def clock_health() -> dict:
    try:
        raw = read_kernel_clock()
        result = evaluate(raw)
        result["platform"] = platform.platform()
        result["sampled_at"] = datetime.now(timezone.utc).isoformat()
        return result
    except Exception as exc:
        return {
            "clock_source": "linux-kernel-adjtimex+ntp_gettime",
            "clock_offset_ms": None,
            "clock_uncertainty_ms": None,
            "evidence_clock_eligible": False,
            "read_only": True,
            "detail": f"{type(exc).__name__}: {exc}",
            "platform": platform.platform(),
            "sampled_at": datetime.now(timezone.utc).isoformat(),
        }


if __name__ == "__main__":
    print(json.dumps(clock_health(), indent=2, sort_keys=True))
