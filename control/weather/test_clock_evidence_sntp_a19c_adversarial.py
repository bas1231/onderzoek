#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control" / "weather"))

import clock_evidence_sntp_a19c as c


def _packet(*, request_tx: int, t2_ns: int, t3_ns: int, leap: int = 0, version: int = 4, mode: int = 4, stratum: int = 2, root_delay_ms: float = 10.0, root_disp_ms: float = 2.0, originate_override: int | None = None, zero_tx: bool = False) -> bytes:
    data = bytearray(48)
    data[0] = ((leap & 3) << 6) | ((version & 7) << 3) | (mode & 7)
    data[1] = stratum & 0xFF
    data[4:8] = struct.pack('!i', int(round(root_delay_ms / 1000.0 * 65536.0)))
    data[8:12] = struct.pack('!I', int(round(root_disp_ms / 1000.0 * 65536.0)))
    data[24:32] = struct.pack('!Q', request_tx if originate_override is None else originate_override)
    data[32:40] = struct.pack('!Q', c.unix_ns_to_ntp64(t2_ns))
    data[40:48] = b'\x00' * 8 if zero_tx else struct.pack('!Q', c.unix_ns_to_ntp64(t3_ns))
    return bytes(data)


def _parse(**kwargs):
    t1 = 1_790_010_000_000_000_000
    t2 = t1 + 10_000_000
    t3 = t2 + 1_000_000
    t4 = t1 + 21_000_000
    tx = c.unix_ns_to_ntp64(t1)
    return c.parse_reply(
        _packet(request_tx=tx, t2_ns=t2, t3_ns=t3, **kwargs),
        host='evil.example', server_ip='192.0.2.10', request_tx=tx,
        t1_wall_ns=t1, t4_wall_ns=t4,
        t1_mono_ns=5_000_000_000, t4_mono_ns=5_021_000_000,
    )


def expect_reject(**kwargs):
    try:
        _parse(**kwargs)
    except ValueError:
        return
    raise AssertionError(f'expected rejection for {kwargs!r}')


def test_unsynchronized_leap_alarm_rejected():
    expect_reject(leap=3)


def test_stratum_zero_kiss_of_death_rejected():
    expect_reject(stratum=0)


def test_non_server_mode_rejected():
    expect_reject(mode=3)


def test_origin_timestamp_mismatch_rejected():
    expect_reject(originate_override=123)


def test_zero_transmit_timestamp_rejected():
    expect_reject(zero_tx=True)


def test_implausible_root_dispersion_rejected():
    expect_reject(root_disp_ms=1500.0)


def test_outlier_server_expands_consensus_bound_fail_closed():
    def s(ip: str, offset: float):
        return c.SntpSample(
            host='x', server_ip=ip, version=4, leap=0, stratum=2,
            offset_ms=offset, delay_ms=10.0, root_delay_ms=2.0,
            root_dispersion_ms=1.0, wall_monotonic_divergence_ms=0.0,
            sample_uncertainty_ms=8.0,
        )
    out = c.aggregate_samples([
        s('192.0.2.1', 1.0), s('192.0.2.2', 2.0), s('192.0.2.3', 250.0)
    ])
    assert out['evidence_clock_eligible'] is False
    assert out['clock_uncertainty_ms'] > 100.0


if __name__ == '__main__':
    tests = [
        test_unsynchronized_leap_alarm_rejected,
        test_stratum_zero_kiss_of_death_rejected,
        test_non_server_mode_rejected,
        test_origin_timestamp_mismatch_rejected,
        test_zero_transmit_timestamp_rejected,
        test_implausible_root_dispersion_rejected,
        test_outlier_server_expands_consensus_bound_fail_closed,
    ]
    for test in tests:
        test()
    print(f'CLOCK_EVIDENCE_SNTP_A19C_ADVERSARIAL_TESTS_PASS {len(tests)}')
