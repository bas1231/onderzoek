#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control" / "weather"))

import clock_evidence_sntp_a19c as base
import clock_evidence_transport_a19d as a19d


def expect_value_error(fn):
    try:
        fn()
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def sample(host: str, ip: str, offset: float = 1.0) -> base.SntpSample:
    return base.SntpSample(
        host=host,
        server_ip=ip,
        version=4,
        leap=0,
        stratum=2,
        offset_ms=offset,
        delay_ms=10.0,
        root_delay_ms=2.0,
        root_dispersion_ms=1.0,
        wall_monotonic_divergence_ms=0.0,
        sample_uncertainty_ms=8.0,
    )


def valid_packet(request_tx: int, t2_ns: int, t3_ns: int) -> bytes:
    data = bytearray(48)
    data[0] = (4 << 3) | 4
    data[1] = 2
    data[4:8] = struct.pack("!i", int(0.010 * 65536))
    data[8:12] = struct.pack("!I", int(0.002 * 65536))
    data[24:32] = struct.pack("!Q", request_tx)
    data[32:40] = struct.pack("!Q", base.unix_ns_to_ntp64(t2_ns))
    data[40:48] = struct.pack("!Q", base.unix_ns_to_ntp64(t3_ns))
    return bytes(data)


def test_truncated_ntp_packet_rejected():
    t1 = 1_790_010_000_000_000_000
    tx = base.unix_ns_to_ntp64(t1)
    expect_value_error(lambda: base.parse_reply(
        b"\x24" * 47,
        host="bad",
        server_ip="192.0.2.1",
        request_tx=tx,
        t1_wall_ns=t1,
        t4_wall_ns=t1 + 10_000_000,
        t1_mono_ns=1_000_000_000,
        t4_mono_ns=1_010_000_000,
    ))


def test_negative_client_delay_rejected():
    t1 = 1_790_010_000_000_000_000
    # Server claims 30 ms elapsed while only 10 ms elapsed client-side.
    t2 = t1 + 1_000_000
    t3 = t2 + 30_000_000
    t4 = t1 + 10_000_000
    tx = base.unix_ns_to_ntp64(t1)
    packet = valid_packet(tx, t2, t3)
    expect_value_error(lambda: base.parse_reply(
        packet,
        host="bad",
        server_ip="192.0.2.1",
        request_tx=tx,
        t1_wall_ns=t1,
        t4_wall_ns=t4,
        t1_mono_ns=1_000_000_000,
        t4_mono_ns=1_010_000_000,
    ))


def test_two_provider_round_cannot_open_gate():
    mapping = {
        "a": sample("a", "192.0.2.1"),
        "b": sample("b", "192.0.2.2"),
    }
    out = a19d.collect_round(("a", "b", "c"), query=lambda host: mapping[host])
    assert out["provider_count"] == 2
    assert out["evidence_clock_eligible"] is False
    assert "c" in out["errors"]


def test_single_bad_round_blocks_five_round_gate():
    good = {
        "evidence_clock_eligible": True,
        "clock_offset_ms": 1.0,
        "clock_total_error_bound_ms": 20.0,
    }
    bad = {
        "evidence_clock_eligible": False,
        "clock_offset_ms": None,
        "clock_total_error_bound_ms": None,
    }
    out = a19d.aggregate_rounds([good, good, bad, good, good], required_rounds=5)
    assert out["eligible_round_count"] == 4
    assert out["evidence_clock_eligible"] is False
    assert "not all consecutive" in out["detail"]


def test_large_per_round_error_bound_blocks_final_gate():
    rounds = [
        {
            "evidence_clock_eligible": True,
            "clock_offset_ms": 1.0,
            "clock_total_error_bound_ms": 105.0,
        }
        for _ in range(5)
    ]
    out = a19d.aggregate_rounds(rounds, required_rounds=5)
    assert out["evidence_clock_eligible"] is False
    assert out["clock_total_error_bound_ms"] > 100.0


if __name__ == "__main__":
    tests = [
        test_truncated_ntp_packet_rejected,
        test_negative_client_delay_rejected,
        test_two_provider_round_cannot_open_gate,
        test_single_bad_round_blocks_five_round_gate,
        test_large_per_round_error_bound_blocks_final_gate,
    ]
    for test in tests:
        test()
    print(f"CLOCK_EVIDENCE_TRANSPORT_A19D_ADVERSARIAL_TESTS_PASS {len(tests)}")
