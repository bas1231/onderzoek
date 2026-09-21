#!/usr/bin/env python3
from __future__ import annotations

import io
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control" / "weather"))

import madis_ldm_queue_native_a19b_v2 as base
import madis_ldm_queue_native_a19b_v2_strict as strict


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


def good_clock():
    return {
        "clock_source": "test-clock",
        "clock_offset_ms": 0.1,
        "clock_uncertainty_ms": 1.0,
        "evidence_clock_eligible": True,
    }


def parse(flags: int = 0):
    raw = strict.build_test_frame(b"x", flags=flags)
    frame = strict.read_frame(io.BytesIO(raw))
    assert frame is not None
    return frame


def with_fake_decode(fn):
    old_archive = base.archive_and_decode
    old_clock = base.clock_health
    try:
        base.archive_and_decode = lambda data, stations: (fake_decode(), False)
        base.clock_health = good_clock
        return fn()
    finally:
        base.archive_and_decode = old_archive
        base.clock_health = old_clock


def test_clean_live_frame_is_eligible():
    def body():
        result = strict.ingest_frame(parse(), mode="ldm-queue-native", stations={"KMIA"})
        assert result["status"] == "PASS"
        assert result["queue_capture_gap_risk"] is False
        assert result["eligible_for_queue_insertion_latency_analysis"] is True
        assert result["strict_provenance_gate"]["pass_for_latency"] is True
    with_fake_decode(body)


def test_full_plus_early_cursor_is_not_latency_evidence():
    flags = strict.FLAG_EARLY_CURSOR | strict.FLAG_QUEUE_FULL
    def body():
        result = strict.ingest_frame(parse(flags), mode="ldm-queue-native", stations={"KMIA"})
        assert result["status"] == "PASS"
        assert result["queue_capture_gap_risk"] is True
        assert result["eligible_for_queue_insertion_latency_analysis"] is False
        assert result["eligible_for_adapter_first_seen_latency_analysis"] is False
        assert result["strict_provenance_gate"]["pass_for_latency"] is False
    with_fake_decode(body)


def test_early_cursor_without_full_queue_is_not_automatically_rejected():
    def body():
        result = strict.ingest_frame(
            parse(strict.FLAG_EARLY_CURSOR),
            mode="ldm-queue-native",
            stations={"KMIA"},
        )
        assert result["queue_capture_gap_risk"] is False
        assert result["eligible_for_queue_insertion_latency_analysis"] is True
    with_fake_decode(body)


def test_full_queue_without_early_cursor_is_not_automatically_rejected():
    def body():
        result = strict.ingest_frame(
            parse(strict.FLAG_QUEUE_FULL),
            mode="ldm-queue-native",
            stations={"KMIA"},
        )
        assert result["queue_capture_gap_risk"] is False
        assert result["eligible_for_queue_insertion_latency_analysis"] is True
    with_fake_decode(body)


def test_replay_remains_ineligible_under_strict_gate():
    def body():
        result = strict.ingest_frame(parse(), mode="replay", stations={"KMIA"})
        assert result["eligible_for_queue_insertion_latency_analysis"] is False
        assert result["eligible_for_adapter_first_seen_latency_analysis"] is False
    with_fake_decode(body)


if __name__ == "__main__":
    tests = [
        test_clean_live_frame_is_eligible,
        test_full_plus_early_cursor_is_not_latency_evidence,
        test_early_cursor_without_full_queue_is_not_automatically_rejected,
        test_full_queue_without_early_cursor_is_not_automatically_rejected,
        test_replay_remains_ineligible_under_strict_gate,
    ]
    for test in tests:
        test()
    print(f"MADIS_LDM_QUEUE_NATIVE_A19B_V2_STRICT_UNIT_TESTS_PASS {len(tests)}")
