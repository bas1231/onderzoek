#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control" / "weather"))

import madis_ldm_ingest_a19b as m


def build_packet(payload: bytes) -> bytes:
    ident = b"TEST"
    origin = b"ORIGIN"
    body = b"".join([
        hashlib.md5(payload).digest(),
        struct.pack("=I", len(payload)),
        struct.pack("=Q", 1_790_010_000),
        struct.pack("=i", 0),
        struct.pack("=I", 1),
        struct.pack("=I", 1),
        struct.pack("=I", len(ident)), ident,
        struct.pack("=I", len(origin)), origin,
    ])
    return struct.pack("=I", len(body) + 4) + body + payload


def timing():
    return {
        "adapter_first_seen_at_ns": 1_790_010_001_000_000_000,
        "adapter_first_seen_at": "2026-09-21T17:00:01+00:00",
        "adapter_first_seen_monotonic_ns": 1,
        "adapter_read_complete_at_ns": 1_790_010_001_001_000_000,
        "adapter_read_complete_at": "2026-09-21T17:00:01.001000+00:00",
        "adapter_read_complete_monotonic_ns": 1_001_000,
        "adapter_read_duration_ms": 1.0,
    }


def good_decode(data, stations):
    return ({
        "status": "PASS",
        "raw_sha256": "abc",
        "decode": {
            "status": "PASS",
            "matched_station_count": 1,
            "matched_rows": [{"station": "KMIA", "observation_time_raw": 1_790_010_000.0}],
        },
    }, False)


def test_corrupt_signature_rejected():
    packet = bytearray(build_packet(b"CDF\x01abc"))
    packet[-1] ^= 1
    try:
        m.parse_pqact_metadata_packet(bytes(packet))
    except ValueError as exc:
        assert "signature mismatch" in str(exc)
    else:
        raise AssertionError("signature mismatch was accepted")


def test_truncated_metadata_rejected():
    try:
        m.parse_pqact_metadata_packet(b"\x00" * 12)
    except ValueError:
        pass
    else:
        raise AssertionError("truncated metadata was accepted")


def test_bad_clock_blocks_adapter_evidence():
    old_clock, old_archive = m.clock_health, m.archive_and_decode
    try:
        m.clock_health = lambda: {
            "clock_source": "chrony:test",
            "clock_offset_ms": 500.0,
            "clock_uncertainty_ms": 700.0,
            "evidence_clock_eligible": False,
        }
        m.archive_and_decode = good_decode
        result = m.ingest_payload(b"x", timing(), mode="ldm-pipe", metadata={"product_identifier": "TEST"}, stations={"KMIA"})
        assert result["status"] == "PASS"
        assert result["eligible_for_adapter_first_seen_latency_analysis"] is False
        assert result["eligible_for_queue_insertion_latency_analysis"] is False
    finally:
        m.clock_health, m.archive_and_decode = old_clock, old_archive


def test_duplicate_product_blocks_adapter_evidence():
    old_clock, old_archive = m.clock_health, m.archive_and_decode
    try:
        m.clock_health = lambda: {
            "clock_source": "chrony:test",
            "clock_offset_ms": 0.0,
            "clock_uncertainty_ms": 1.0,
            "evidence_clock_eligible": True,
        }
        m.archive_and_decode = lambda data, stations: (good_decode(data, stations)[0], True)
        result = m.ingest_payload(b"x", timing(), mode="ldm-pipe", metadata={"product_identifier": "TEST"}, stations={"KMIA"})
        assert result["duplicate_product"] is True
        assert result["eligible_for_adapter_first_seen_latency_analysis"] is False
    finally:
        m.clock_health, m.archive_and_decode = old_clock, old_archive


def test_live_good_clock_allows_adapter_only_not_queue_evidence():
    old_clock, old_archive = m.clock_health, m.archive_and_decode
    try:
        m.clock_health = lambda: {
            "clock_source": "chrony:test",
            "clock_offset_ms": 0.1,
            "clock_uncertainty_ms": 2.0,
            "evidence_clock_eligible": True,
        }
        m.archive_and_decode = good_decode
        result = m.ingest_payload(b"x", timing(), mode="ldm-pipe", metadata={"product_identifier": "TEST"}, stations={"KMIA"})
        assert result["eligible_for_adapter_first_seen_latency_analysis"] is True
        assert result["eligible_for_queue_insertion_latency_analysis"] is False
        assert result["ldm_queue_insert_at"] is None
        assert result["queue_insert_to_adapter_first_seen_ms"] is None
    finally:
        m.clock_health, m.archive_and_decode = old_clock, old_archive


if __name__ == "__main__":
    tests = [
        test_corrupt_signature_rejected,
        test_truncated_metadata_rejected,
        test_bad_clock_blocks_adapter_evidence,
        test_duplicate_product_blocks_adapter_evidence,
        test_live_good_clock_allows_adapter_only_not_queue_evidence,
    ]
    for test in tests:
        test()
    print(f"MADIS_LDM_A19B_ADVERSARIAL_TESTS_PASS {len(tests)}")
