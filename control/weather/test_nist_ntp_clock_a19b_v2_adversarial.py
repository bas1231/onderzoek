#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control" / "weather"))

import nist_ntp_clock_a19b_v2 as m


def fixed(value: float, signed: bool) -> bytes:
    raw = int(round(value * 65536.0))
    return struct.pack("!i" if signed else "!I", raw)


def make_packet(
    tx: bytes,
    t2: float,
    t3: float,
    *,
    li: int = 0,
    mode: int = 4,
    stratum: int = 1,
    root_delay: float = 0.005,
    root_dispersion: float = 0.002,
) -> bytes:
    p = bytearray(48)
    p[0] = ((li & 3) << 6) | (4 << 3) | (mode & 7)
    p[1] = stratum
    p[4:8] = fixed(root_delay, True)
    p[8:12] = fixed(root_dispersion, False)
    p[24:32] = tx
    p[32:40] = m._unix_to_ntp64(t2)
    p[40:48] = m._unix_to_ntp64(t3)
    return bytes(p)


def must_fail(packet: bytes, tx: bytes, t1: float, t4: float) -> None:
    try:
        m.parse_response(
            packet,
            request_tx=tx,
            t1_unix=t1,
            t4_unix=t4,
            server_name="test.nist.gov",
            server_ip="192.0.2.1",
        )
    except m.NtpEvidenceError:
        return
    raise AssertionError("malformed/unsafe NTP sample was accepted")


def sample(name: str, ip: str, low: float, high: float) -> dict:
    return {
        "status": "PASS",
        "server_name": name,
        "server_ip": ip,
        "stratum": 1,
        "correction_interval_low_ms": low,
        "correction_interval_high_ms": high,
        "individual_absolute_error_bound_ms": max(abs(low), abs(high)),
    }


def test_truncated_response_fails_closed():
    t1 = 1_790_038_400.0
    _, tx = m.build_request(t1)
    must_fail(b"\x24" * 20, tx, t1, t1 + 0.02)


def test_spoofed_originate_fails_closed():
    t1 = 1_790_038_400.0
    _, tx = m.build_request(t1)
    p = bytearray(make_packet(tx, t1 + 0.01, t1 + 0.011))
    p[24:32] = b"BADSTAMP"
    must_fail(bytes(p), tx, t1, t1 + 0.021)


def test_unsynchronized_server_fails_closed():
    t1 = 1_790_038_400.0
    _, tx = m.build_request(t1)
    must_fail(make_packet(tx, t1 + 0.01, t1 + 0.011, li=3), tx, t1, t1 + 0.021)


def test_non_stratum1_or_wrong_mode_fails_closed():
    t1 = 1_790_038_400.0
    _, tx = m.build_request(t1)
    must_fail(make_packet(tx, t1 + 0.01, t1 + 0.011, stratum=2), tx, t1, t1 + 0.021)
    must_fail(make_packet(tx, t1 + 0.01, t1 + 0.011, mode=3), tx, t1, t1 + 0.021)


def test_material_negative_path_delay_fails_closed():
    t1 = 1_790_038_400.0
    _, tx = m.build_request(t1)
    # Server processing interval is 50 ms while client elapsed is 10 ms.
    must_fail(make_packet(tx, t1 + 0.001, t1 + 0.051), tx, t1, t1 + 0.010)


def test_large_bound_and_duplicate_source_block_gate():
    rows = [
        sample("a", "1.1.1.1", -120.0, 80.0),
        sample("b", "1.1.1.1", -20.0, 20.0),
        sample("c", "3.3.3.3", -20.0, 20.0),
    ]
    out = m.evaluate_samples(rows, expected_count=3)
    assert out["evidence_clock_eligible"] is False
    assert "SAMPLE_0_BOUND_ABOVE_LIMIT" in out["reasons"]
    assert "NIST_SERVER_IP_DIVERSITY_FAILED" in out["reasons"]


def test_disjoint_source_intervals_block_gate():
    rows = [
        sample("a", "1.1.1.1", -10.0, 10.0),
        sample("b", "2.2.2.2", 20.0, 30.0),
        sample("c", "3.3.3.3", -5.0, 5.0),
    ]
    out = m.evaluate_samples(rows, expected_count=3)
    assert out["evidence_clock_eligible"] is False
    assert "NO_COMMON_UTC_CORRECTION_INTERVAL" in out["reasons"]


def test_missing_source_blocks_gate():
    rows = [
        sample("a", "1.1.1.1", -10.0, 10.0),
        sample("b", "2.2.2.2", -10.0, 10.0),
        {"status": "BLOCKED", "server_name": "c", "reason": "timeout"},
    ]
    out = m.evaluate_samples(rows, expected_count=3)
    assert out["evidence_clock_eligible"] is False
    assert "NOT_ALL_NIST_SOURCES_VALID" in out["reasons"]


if __name__ == "__main__":
    tests = [
        test_truncated_response_fails_closed,
        test_spoofed_originate_fails_closed,
        test_unsynchronized_server_fails_closed,
        test_non_stratum1_or_wrong_mode_fails_closed,
        test_material_negative_path_delay_fails_closed,
        test_large_bound_and_duplicate_source_block_gate,
        test_disjoint_source_intervals_block_gate,
        test_missing_source_blocks_gate,
    ]
    for test in tests:
        test()
    print(f"A19B_NIST_NTP_CLOCK_ADVERSARIAL_TESTS_PASS {len(tests)}")
