#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control" / "weather"))

import nist_ntp_clock_a19b_v2 as m


def ntp64(ts: float) -> bytes:
    return m._unix_to_ntp64(ts)


def fixed_16_16(value: float, *, signed: bool) -> bytes:
    raw = int(round(value * 65536.0))
    return struct.pack("!i" if signed else "!I", raw)


def response(
    request_tx: bytes,
    *,
    t2: float,
    t3: float,
    root_delay_s: float = 0.010,
    root_dispersion_s: float = 0.005,
    li: int = 0,
    version: int = 4,
    mode: int = 4,
    stratum: int = 1,
) -> bytes:
    p = bytearray(48)
    p[0] = ((li & 3) << 6) | ((version & 7) << 3) | (mode & 7)
    p[1] = stratum
    p[4:8] = fixed_16_16(root_delay_s, signed=True)
    p[8:12] = fixed_16_16(root_dispersion_s, signed=False)
    p[12:16] = b"GPS\x00"
    p[24:32] = request_tx
    p[32:40] = ntp64(t2)
    p[40:48] = ntp64(t3)
    return bytes(p)


def parsed_sample(name: str, ip: str, offset_ms: float, radius_ms: float) -> dict:
    low = offset_ms - radius_ms
    high = offset_ms + radius_ms
    return {
        "status": "PASS",
        "server_name": name,
        "server_ip": ip,
        "stratum": 1,
        "correction_interval_low_ms": low,
        "correction_interval_high_ms": high,
        "individual_absolute_error_bound_ms": max(abs(low), abs(high)),
    }


def test_timestamp_roundtrip():
    value = 1_790_038_400.123456
    raw = m._unix_to_ntp64(value)
    decoded = m._ntp64_to_unix(raw)
    assert abs(decoded - value) < 1e-6


def test_response_math_and_signed_root_delay():
    t1 = 1_790_038_400.000
    request, tx = m.build_request(t1)
    assert len(request) == 48
    # Symmetric 40 ms network path; server is 12 ms ahead of local clock.
    # t2 = t1 + 20 ms propagation + 12 ms offset
    # t3 = t2 + 2 ms processing
    # t4 = t1 + 42 ms total local elapsed
    packet = response(
        tx,
        t2=t1 + 0.032,
        t3=t1 + 0.034,
        root_delay_s=-0.004,
        root_dispersion_s=0.003,
    )
    out = m.parse_response(
        packet,
        request_tx=tx,
        t1_unix=t1,
        t4_unix=t1 + 0.042,
        server_name="time-a-g.nist.gov",
        server_ip="129.6.15.28",
    )
    assert abs(out["offset_ms"] - 12.0) < 0.02
    assert abs(out["path_delay_ms"] - 40.0) < 0.02
    assert abs(out["root_delay_ms"] - (-4.0)) < 0.02
    assert abs(out["root_distance_ms"] - 5.0) < 0.03
    # 5 ms root distance + 20 ms half path + 1 ms serialization guard.
    assert abs(out["uncertainty_radius_ms"] - 26.0) < 0.05
    assert out["individual_absolute_error_bound_ms"] < 39.0


def test_three_source_consensus_is_eligible():
    rows = [
        parsed_sample("a", "1.1.1.1", 3.0, 20.0),
        parsed_sample("b", "2.2.2.2", -2.0, 22.0),
        parsed_sample("c", "3.3.3.3", 1.0, 18.0),
    ]
    out = m.evaluate_samples(rows, expected_count=3)
    assert out["decision"] == "CLOCK_EVIDENCE_ELIGIBLE"
    assert out["evidence_clock_eligible"] is True
    assert out["consensus_correction_interval_low_ms"] == -17.0
    assert out["consensus_correction_interval_high_ms"] == 19.0
    assert out["consensus_absolute_error_bound_ms"] == 19.0


def test_no_system_clock_mutation_api_in_probe_contract():
    result = {
        "changes_system_clock": False,
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
    }
    assert result["changes_system_clock"] is False
    assert not any(result[k] for k in ("live_trading", "paid_action", "wallet_action"))


if __name__ == "__main__":
    tests = [
        test_timestamp_roundtrip,
        test_response_math_and_signed_root_delay,
        test_three_source_consensus_is_eligible,
        test_no_system_clock_mutation_api_in_probe_contract,
    ]
    for test in tests:
        test()
    print(f"A19B_NIST_NTP_CLOCK_UNIT_TESTS_PASS {len(tests)}")
