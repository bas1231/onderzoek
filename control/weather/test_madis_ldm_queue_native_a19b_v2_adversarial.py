#!/usr/bin/env python3
from __future__ import annotations

import io
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control" / "weather"))

import madis_ldm_queue_native_a19b_v2 as q


def must_fail(raw: bytes, contains: str | None = None):
    try:
        q.read_frame(io.BytesIO(raw))
    except Exception as exc:
        if contains is not None:
            assert contains.lower() in str(exc).lower(), (contains, str(exc))
        return
    raise AssertionError("malformed queue-native frame was accepted")


def test_bad_magic_rejected():
    raw = bytearray(q.build_test_frame(b"x"))
    raw[0] ^= 0x01
    must_fail(bytes(raw), "magic")


def test_unknown_version_rejected():
    raw = q.build_test_frame(b"x", version=99)
    must_fail(raw, "version")


def test_truncated_payload_rejected():
    raw = q.build_test_frame(b"abcdef")
    must_fail(raw[:-2], "truncated")


def test_product_size_disagreement_rejected():
    raw = q.build_test_frame(b"abcdef", info_size_override=5)
    must_fail(raw, "size mismatch")


def test_future_queue_insert_rejected():
    now = time.time_ns()
    raw = q.build_test_frame(
        b"x",
        queue_insert_at_ns=now + 10_000_000,
        callback_realtime_ns=now,
    )
    must_fail(raw, "after queue-reader callback")


def test_declared_payload_over_safety_limit_rejected_before_read():
    raw = q.build_test_frame(
        b"x",
        payload_len_override=q.MAX_PRODUCT_BYTES + 1,
        info_size_override=q.MAX_PRODUCT_BYTES + 1,
    )
    must_fail(raw, "safety limit")


def test_invalid_utf8_identifier_rejected():
    raw = bytearray(q.build_test_frame(b"x", product_identifier="A"))
    # Prefix is fixed length; first metadata byte is identifier data.
    raw[q.PREFIX.size] = 0xff
    must_fail(bytes(raw), "UTF-8")


if __name__ == "__main__":
    tests = [
        test_bad_magic_rejected,
        test_unknown_version_rejected,
        test_truncated_payload_rejected,
        test_product_size_disagreement_rejected,
        test_future_queue_insert_rejected,
        test_declared_payload_over_safety_limit_rejected_before_read,
        test_invalid_utf8_identifier_rejected,
    ]
    for test in tests:
        test()
    print(f"MADIS_LDM_QUEUE_NATIVE_A19B_V2_ADVERSARIAL_TESTS_PASS {len(tests)}")
