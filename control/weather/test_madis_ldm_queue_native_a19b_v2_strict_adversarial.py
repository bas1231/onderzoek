#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import io
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control" / "weather"))

import madis_ldm_queue_native_a19b_v2 as base
import madis_ldm_queue_native_a19b_v2_strict as strict


def must_fail(raw: bytes, contains: str):
    try:
        strict.read_frame(io.BytesIO(raw))
    except Exception as exc:
        assert contains.lower() in str(exc).lower(), (contains, str(exc))
        return
    raise AssertionError("unsafe queue-native frame was accepted")


def test_signature_mismatch_rejected():
    raw = strict.build_test_frame(b"payload", signature=b"0" * 16)
    must_fail(raw, "signature")


def test_unknown_flag_rejected():
    raw = strict.build_test_frame(b"x", flags=1 << 2)
    must_fail(raw, "flags")


def test_nonpositive_product_metadata_time_rejected():
    now = time.time_ns()
    raw = strict.build_test_frame(
        b"x",
        queue_insert_at_ns=now - 2_000_000,
        product_metadata_time_ns=0,
        callback_realtime_ns=now,
    )
    must_fail(raw, "product metadata time")


def test_valid_signature_is_accepted():
    payload = b"valid"
    raw = strict.build_test_frame(payload, signature=hashlib.md5(payload).digest())
    frame = strict.read_frame(io.BytesIO(raw))
    assert frame is not None
    assert frame.payload == payload


def test_base_malformed_frame_rules_still_apply():
    raw = bytearray(strict.build_test_frame(b"x"))
    raw[0] ^= 1
    must_fail(bytes(raw), "magic")


if __name__ == "__main__":
    tests = [
        test_signature_mismatch_rejected,
        test_unknown_flag_rejected,
        test_nonpositive_product_metadata_time_rejected,
        test_valid_signature_is_accepted,
        test_base_malformed_frame_rules_still_apply,
    ]
    for test in tests:
        test()
    print(f"MADIS_LDM_QUEUE_NATIVE_A19B_V2_STRICT_ADVERSARIAL_TESTS_PASS {len(tests)}")
