#!/usr/bin/env python3
from __future__ import annotations

import io
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control" / "weather"))

import madis_ldm_queue_native_a19b_v2 as q


def fake_decode():
    return {
        "status": "PASS",
        "raw_sha256": "abc",
        "decode": {
            "status": "PASS",
            "matched_station_count": 1,
            "matched_stations": ["KMIA"],
            "requested_station_coverage_fraction": 1.0,
            "matched_rows": [{
                "station": "KMIA",
                "observation_time_raw": time.time() - 2.0,
            }],
        },
    }


def _microsecond_aligned_now_ns() -> int:
    """Match LDM queue timeval precision so exact-lag fixtures are deterministic."""
    return (time.time_ns() // 1000) * 1000


def parsed_frame(payload: bytes = b"x", lag_ms: int = 5):
    callback = _microsecond_aligned_now_ns() - 2_000_000
    raw = q.build_test_frame(
        payload,
        queue_insert_at_ns=callback - lag_ms * 1_000_000,
        callback_realtime_ns=callback,
        product_identifier="HF-ASOS-KMIA",
        product_origin="madis-test",
    )
    frame = q.read_frame(io.BytesIO(raw))
    assert frame is not None
    return frame


def test_frame_roundtrip_preserves_queue_timestamp():
    frame = parsed_frame(b"CDF\x01queue-native", lag_ms=8)
    assert frame.payload == b"CDF\x01queue-native"
    assert frame.product_identifier == "HF-ASOS-KMIA"
    assert frame.product_origin == "madis-test"
    assert frame.queue_insert_to_callback_ms == 8.0


def test_timeval_precision_is_explicit_not_flaky():
    # Queue insertion is serialized as timeval (microseconds). A deliberately
    # non-aligned nanosecond input is truncated exactly as the real LDM API is.
    callback = 1_790_010_000_000_000_789
    queue = callback - 8_000_000
    raw = q.build_test_frame(
        b"x",
        queue_insert_at_ns=queue,
        callback_realtime_ns=callback,
    )
    frame = q.read_frame(io.BytesIO(raw))
    assert frame is not None
    assert frame.queue_insert_at_ns == (queue // 1000) * 1000
    assert frame.queue_insert_to_callback_ms == 8.001


def test_live_queue_native_can_be_latency_evidence():
    old_archive, old_clock = q.archive_and_decode, q.clock_health
    try:
        q.archive_and_decode = lambda data, stations: (fake_decode(), False)
        q.clock_health = lambda: {
            "clock_source": "test-clock",
            "clock_offset_ms": 0.1,
            "clock_uncertainty_ms": 1.0,
            "evidence_clock_eligible": True,
        }
        result = q.ingest_frame(parsed_frame(lag_ms=5), mode="ldm-queue-native", stations={"KMIA"})
        assert result["status"] == "PASS"
        assert result["ldm_queue_insert_source"] == "LDM_PQ_NEXT_QUEUE_PAR_T_INSERTED"
        assert result["eligible_for_queue_insertion_latency_analysis"] is True
        assert result["eligible_for_adapter_first_seen_latency_analysis"] is True
        assert result["queue_insert_to_reader_callback_ms"] == 5.0
    finally:
        q.archive_and_decode, q.clock_health = old_archive, old_clock


def test_replay_is_never_latency_evidence():
    old_archive, old_clock = q.archive_and_decode, q.clock_health
    try:
        q.archive_and_decode = lambda data, stations: (fake_decode(), False)
        q.clock_health = lambda: {
            "clock_source": "test-clock",
            "clock_offset_ms": 0.0,
            "clock_uncertainty_ms": 0.0,
            "evidence_clock_eligible": True,
        }
        result = q.ingest_frame(parsed_frame(), mode="replay", stations={"KMIA"})
        assert result["status"] == "PASS"
        assert result["eligible_for_queue_insertion_latency_analysis"] is False
        assert result["eligible_for_adapter_first_seen_latency_analysis"] is False
        assert result["ldm_queue_insert_at_ns"] is not None
    finally:
        q.archive_and_decode, q.clock_health = old_archive, old_clock


def test_bad_clock_fails_closed():
    old_archive, old_clock = q.archive_and_decode, q.clock_health
    try:
        q.archive_and_decode = lambda data, stations: (fake_decode(), False)
        q.clock_health = lambda: {
            "clock_source": None,
            "clock_offset_ms": None,
            "clock_uncertainty_ms": None,
            "evidence_clock_eligible": False,
        }
        result = q.ingest_frame(parsed_frame(), mode="ldm-queue-native", stations={"KMIA"})
        assert result["status"] == "PASS"
        assert result["eligible_for_queue_insertion_latency_analysis"] is False
    finally:
        q.archive_and_decode, q.clock_health = old_archive, old_clock


def test_duplicate_fails_closed_for_latency():
    old_archive, old_clock = q.archive_and_decode, q.clock_health
    try:
        q.archive_and_decode = lambda data, stations: (fake_decode(), True)
        q.clock_health = lambda: {
            "clock_source": "test-clock",
            "clock_offset_ms": 0.0,
            "clock_uncertainty_ms": 1.0,
            "evidence_clock_eligible": True,
        }
        result = q.ingest_frame(parsed_frame(), mode="ldm-queue-native", stations={"KMIA"})
        assert result["status"] == "PASS"
        assert result["duplicate_raw_product"] is True
        assert result["eligible_for_queue_insertion_latency_analysis"] is False
    finally:
        q.archive_and_decode, q.clock_health = old_archive, old_clock


def test_clean_eof_is_not_a_frame():
    assert q.read_frame(io.BytesIO(b"")) is None


if __name__ == "__main__":
    tests = [
        test_frame_roundtrip_preserves_queue_timestamp,
        test_timeval_precision_is_explicit_not_flaky,
        test_live_queue_native_can_be_latency_evidence,
        test_replay_is_never_latency_evidence,
        test_bad_clock_fails_closed,
        test_duplicate_fails_closed_for_latency,
        test_clean_eof_is_not_a_frame,
    ]
    for test in tests:
        test()
    print(f"MADIS_LDM_QUEUE_NATIVE_A19B_V2_UNIT_TESTS_PASS {len(tests)}")
