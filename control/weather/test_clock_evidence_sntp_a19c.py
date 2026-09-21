#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control" / "weather"))

import clock_evidence_sntp_a19c as c


def _reply(*, request_tx: int, t2_ns: int, t3_ns: int, leap: int = 0, version: int = 4, mode: int = 4, stratum: int = 2, root_delay_ms: float = 10.0, root_disp_ms: float = 2.0) -> bytes:
    data = bytearray(48)
    data[0] = ((leap & 0x3) << 6) | ((version & 0x7) << 3) | (mode & 0x7)
    data[1] = stratum & 0xFF
    root_delay = int(round(root_delay_ms / 1000.0 * 65536.0))
    root_disp = int(round(root_disp_ms / 1000.0 * 65536.0))
    data[4:8] = struct.pack('!i', root_delay)
    data[8:12] = struct.pack('!I', root_disp)
    data[24:32] = struct.pack('!Q', request_tx)
    data[32:40] = struct.pack('!Q', c.unix_ns_to_ntp64(t2_ns))
    data[40:48] = struct.pack('!Q', c.unix_ns_to_ntp64(t3_ns))
    return bytes(data)


def test_ntp_timestamp_roundtrip_with_subsecond_precision():
    original = 1_790_010_000_123_456_789
    restored = c.ntp64_to_unix_ns(c.unix_ns_to_ntp64(original))
    assert abs(restored - original) <= 1


def test_parse_reply_recovers_known_offset_and_delay():
    t1 = 1_790_010_000_000_000_000
    # client is 20 ms slow relative to server; 10 ms each direction; 2 ms server work
    t2 = t1 + 30_000_000
    t3 = t2 + 2_000_000
    t4 = t1 + 22_000_000
    tx = c.unix_ns_to_ntp64(t1)
    sample = c.parse_reply(
        _reply(request_tx=tx, t2_ns=t2, t3_ns=t3),
        host='one.example',
        server_ip='192.0.2.1',
        request_tx=tx,
        t1_wall_ns=t1,
        t4_wall_ns=t4,
        t1_mono_ns=10_000_000_000,
        t4_mono_ns=10_022_000_000,
    )
    assert abs(sample.offset_ms - 20.0) < 0.01
    assert abs(sample.delay_ms - 20.0) < 0.01
    assert sample.sample_uncertainty_ms > 0


def _sample(ip: str, offset: float, uncertainty: float = 10.0) -> c.SntpSample:
    return c.SntpSample(
        host='test', server_ip=ip, version=4, leap=0, stratum=2,
        offset_ms=offset, delay_ms=10.0, root_delay_ms=2.0,
        root_dispersion_ms=1.0, wall_monotonic_divergence_ms=0.1,
        sample_uncertainty_ms=uncertainty,
    )


def test_three_server_consensus_can_be_eligible():
    out = c.aggregate_samples([
        _sample('192.0.2.1', 2.0),
        _sample('192.0.2.2', 3.0),
        _sample('192.0.2.3', 1.0),
    ])
    assert out['sample_count'] == 3
    assert out['clock_offset_ms'] == 2.0
    assert out['evidence_clock_eligible'] is True
    assert out['clock_total_error_bound_ms'] <= 100.0


def test_duplicate_server_ip_cannot_manufacture_consensus():
    out = c.aggregate_samples([
        _sample('192.0.2.1', 1.0),
        _sample('192.0.2.1', 2.0, uncertainty=5.0),
        _sample('192.0.2.2', 1.5),
    ])
    assert out['sample_count'] == 2
    assert out['evidence_clock_eligible'] is False


def test_large_known_clock_offset_is_still_ineligible_for_raw_timestamps():
    out = c.aggregate_samples([
        _sample('192.0.2.1', 120.0, 5.0),
        _sample('192.0.2.2', 121.0, 5.0),
        _sample('192.0.2.3', 119.0, 5.0),
    ])
    assert out['evidence_clock_eligible'] is False
    assert out['clock_total_error_bound_ms'] > 100.0


def test_collect_clock_evidence_uses_injected_query_and_records_errors():
    mapping = {
        'a': _sample('192.0.2.1', 1.0),
        'b': _sample('192.0.2.2', 2.0),
        'c': _sample('192.0.2.3', 1.5),
    }
    def query(host: str):
        if host == 'bad':
            raise TimeoutError('test timeout')
        return mapping[host]
    out = c.collect_clock_evidence(('a', 'bad', 'b', 'c'), query=query)
    assert out['evidence_clock_eligible'] is True
    assert 'bad' in out['errors']


if __name__ == '__main__':
    tests = [
        test_ntp_timestamp_roundtrip_with_subsecond_precision,
        test_parse_reply_recovers_known_offset_and_delay,
        test_three_server_consensus_can_be_eligible,
        test_duplicate_server_ip_cannot_manufacture_consensus,
        test_large_known_clock_offset_is_still_ineligible_for_raw_timestamps,
        test_collect_clock_evidence_uses_injected_query_and_records_errors,
    ]
    for test in tests:
        test()
    print(f'CLOCK_EVIDENCE_SNTP_A19C_UNIT_TESTS_PASS {len(tests)}')
