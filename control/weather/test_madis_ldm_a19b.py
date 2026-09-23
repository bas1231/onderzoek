#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import io
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control" / "weather"))

import madis_ldm_ingest_a19b as m


def build_packet(payload: bytes, *, metadata_length_includes_word: bool = True) -> bytes:
    sig = hashlib.md5(payload).digest()
    ident = b"TEST-HF-ASOS"
    origin = b"test-origin"
    body = b"".join([
        sig,
        struct.pack("=I", len(payload)),
        struct.pack("=Q", 1_790_010_000),
        struct.pack("=i", 123_456),
        struct.pack("=I", 7),
        struct.pack("=I", 42),
        struct.pack("=I", len(ident)),
        ident,
        struct.pack("=I", len(origin)),
        origin,
    ])
    declared = len(body) + (4 if metadata_length_includes_word else 0)
    return struct.pack("=I", declared) + body + payload


def test_pqact_metadata_parser_roundtrip():
    payload = b"CDF\x01example"
    metadata, decoded = m.parse_pqact_metadata_packet(build_packet(payload))
    assert decoded == payload
    assert metadata["product_size"] == len(payload)
    assert metadata["sequence_number"] == 42
    assert metadata["product_identifier"] == "TEST-HF-ASOS"
    assert metadata["product_origin"] == "test-origin"
    assert metadata["signature_md5"] == hashlib.md5(payload).hexdigest()
    expected_ns = 1_790_010_000 * 1_000_000_000 + 123_456 * 1000
    assert metadata["product_creation_time_ns"] == expected_ns
    assert "NOT local queue insertion" in metadata["product_creation_time_semantics"]


def test_pqact_metadata_parser_accepts_length_convention_variants():
    payload = b"CDF\x01abc"
    for includes in (True, False):
        metadata, decoded = m.parse_pqact_metadata_packet(
            build_packet(payload, metadata_length_includes_word=includes)
        )
        assert decoded == payload
        assert metadata["product_size"] == len(payload)


def test_chrony_parser_exposes_required_clock_fields():
    text = """Reference ID    : 1.2.3.4
Stratum         : 3
System time     : 0.000250 seconds slow of NTP time
Last offset     : -0.000100 seconds
RMS offset      : 0.000300 seconds
Root delay      : 0.010000 seconds
Root dispersion : 0.002000 seconds
Leap status     : Normal
"""
    out = m.parse_chronyc_tracking(text)
    assert out["clock_source"].startswith("chrony:")
    assert round(out["clock_offset_ms"], 6) == -0.25
    assert round(out["clock_uncertainty_ms"], 6) == 7.25
    assert out["evidence_clock_eligible"] is True


def test_adapter_timing_names_are_semantically_explicit():
    data, timing = m.read_all_with_timing(io.BytesIO(b"abc"))
    assert data == b"abc"
    assert "adapter_first_seen_at_ns" in timing
    assert "adapter_read_complete_at_ns" in timing
    assert all("receipt" not in key for key in timing)


def test_replay_can_never_be_latency_evidence_and_preserves_decode_provenance():
    original_clock = m.clock_health
    original_archive = m.archive_and_decode
    try:
        m.clock_health = lambda: {
            "clock_source": "test",
            "clock_offset_ms": 0.0,
            "clock_uncertainty_ms": 0.0,
            "evidence_clock_eligible": True,
        }
        m.archive_and_decode = lambda data, stations: ({
            "status": "PASS",
            "raw_sha256": "abc",
            "decode": {
                "status": "PASS",
                "matched_station_count": 1,
                "matched_stations": ["KMIA"],
                "requested_station_coverage_fraction": 1.0,
                "matched_rows": [{"station": "KMIA", "observation_time_raw": 1_790_010_000.0}],
            },
        }, False)
        timing = {
            "adapter_first_seen_at_ns": 1_790_010_001_000_000_000,
            "adapter_first_seen_at": datetime(2026, 9, 21, tzinfo=timezone.utc).isoformat(),
            "adapter_first_seen_monotonic_ns": 1,
            "adapter_read_complete_at_ns": 1_790_010_001_000_000_100,
            "adapter_read_complete_at": datetime(2026, 9, 21, tzinfo=timezone.utc).isoformat(),
            "adapter_read_complete_monotonic_ns": 2,
            "adapter_read_duration_ms": 0.001,
        }
        result = m.ingest_payload(b"x", timing, mode="replay", metadata=None, stations={"KMIA"})
        assert result["eligible_for_adapter_first_seen_latency_analysis"] is False
        assert result["eligible_for_queue_insertion_latency_analysis"] is False
        assert result["ldm_queue_insert_at_ns"] is None
        assert "NOT network receipt" in result["adapter_timestamp_semantics"]
        assert result["decode"]["status"] == "PASS"
        assert result["decode"]["decode"]["matched_station_count"] == 1
        assert result["decode"]["decode"]["matched_stations"] == ["KMIA"]
    finally:
        m.clock_health = original_clock
        m.archive_and_decode = original_archive


if __name__ == "__main__":
    tests = [
        test_pqact_metadata_parser_roundtrip,
        test_pqact_metadata_parser_accepts_length_convention_variants,
        test_chrony_parser_exposes_required_clock_fields,
        test_adapter_timing_names_are_semantically_explicit,
        test_replay_can_never_be_latency_evidence_and_preserves_decode_provenance,
    ]
    for test in tests:
        test()
    print(f"MADIS_LDM_A19B_UNIT_TESTS_PASS {len(tests)}")
