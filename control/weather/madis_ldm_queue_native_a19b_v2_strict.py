#!/usr/bin/env python3
"""Strict evidence gate for A19B-v2 queue-native LDM timing.

This wraps the validated frame/decode implementation and adds provenance rules
needed before queue timestamps may be treated as latency evidence:
- LDM product signature must equal MD5(payload);
- only queue flags emitted by the safe reader are accepted;
- a full queue combined with an early cursor signals possible missed products
  and is not latency-eligible;
- replay remains latency-ineligible through the base implementation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from typing import BinaryIO

import madis_ldm_queue_native_a19b_v2 as base

QueueFrame = base.QueueFrame
MAGIC = base.MAGIC
FRAME_VERSION = base.FRAME_VERSION
PREFIX = base.PREFIX
MAX_PRODUCT_BYTES = base.MAX_PRODUCT_BYTES
MAX_TEXT_BYTES = base.MAX_TEXT_BYTES
FLAG_EARLY_CURSOR = base.FLAG_EARLY_CURSOR
FLAG_QUEUE_FULL = base.FLAG_QUEUE_FULL
KNOWN_SAFE_FLAGS = FLAG_EARLY_CURSOR | FLAG_QUEUE_FULL
DEFAULT_STATIONS = base.DEFAULT_STATIONS
build_test_frame = base.build_test_frame
clock_health = base.clock_health
archive_and_decode = base.archive_and_decode


def read_frame(stream: BinaryIO) -> QueueFrame | None:
    frame = base.read_frame(stream)
    if frame is None:
        return None
    unknown = frame.flags & ~KNOWN_SAFE_FLAGS
    if unknown:
        raise ValueError(f"unsupported queue-native flags: 0x{unknown:x}")
    if frame.product_metadata_time_ns <= 0:
        raise ValueError("invalid non-positive product metadata time")
    expected = hashlib.md5(frame.payload).hexdigest()
    if frame.ldm_signature_hex.lower() != expected:
        raise ValueError("LDM product signature does not match payload MD5")
    return frame


def ingest_frame(frame: QueueFrame, *, mode: str, stations: set[str]) -> dict:
    result = base.ingest_frame(frame, mode=mode, stations=stations)
    gap_risk = bool(
        (frame.flags & FLAG_EARLY_CURSOR)
        and (frame.flags & FLAG_QUEUE_FULL)
    )
    result["queue_capture_gap_risk"] = gap_risk
    result["queue_capture_gap_semantics"] = (
        "queue_full AND early_cursor can indicate the cursor predates the oldest retained product; "
        "exclude from latency evidence to avoid silent sample gaps"
    )
    if gap_risk:
        result["eligible_for_queue_insertion_latency_analysis"] = False
        result["eligible_for_adapter_first_seen_latency_analysis"] = False
    result["strict_provenance_gate"] = {
        "ldm_signature_matches_payload_md5": True,
        "known_safe_flags_only": True,
        "queue_capture_gap_risk": gap_risk,
        "pass_for_latency": bool(
            result.get("eligible_for_queue_insertion_latency_analysis")
        ),
    }
    result["queue_evidence_semantics"] = (
        "latency eligibility requires real queue-native mode, nonduplicate decoded product, "
        "eligible local clock evidence, valid LDM signature, known safe flags, and no "
        "queue_full+early_cursor capture-gap risk"
    )
    return result


def persist_evidence(result: dict) -> Path:
    return base.persist_evidence(result)


def _parse_stations(text: str) -> set[str]:
    vals = {v.strip().upper() for v in text.split(",") if v.strip()}
    return vals or set(DEFAULT_STATIONS)


def run_frame_file(path: Path, stations: set[str]) -> dict:
    with path.open("rb") as fh:
        frame = read_frame(fh)
        if frame is None:
            raise ValueError("empty queue-native frame file")
        if fh.read(1) != b"":
            raise ValueError("frame file contains trailing data")
    result = ingest_frame(frame, mode="replay", stations=stations)
    result["evidence_path"] = str(persist_evidence(result))
    return result


def run_live_helper(helper: Path, queue: Path, pattern: str, stations: set[str], *, once: bool) -> int:
    if not helper.is_file():
        raise FileNotFoundError(f"queue-native helper missing: {helper}")
    if not queue.is_file():
        raise FileNotFoundError(f"LDM product queue missing: {queue}")
    cmd = [str(helper), str(queue), pattern]
    if once:
        cmd.append("--once")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=None)
    assert proc.stdout is not None
    emitted = 0
    try:
        while True:
            frame = read_frame(proc.stdout)
            if frame is None:
                break
            result = ingest_frame(frame, mode="ldm-queue-native", stations=stations)
            result["evidence_path"] = str(persist_evidence(result))
            print(json.dumps(result, sort_keys=True), flush=True)
            emitted += 1
            if once:
                break
    finally:
        if once and proc.poll() is None:
            proc.terminate()
        try:
            rc = proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            rc = proc.wait(timeout=5)
    if emitted == 0:
        raise RuntimeError(f"queue-native helper emitted no products; returncode={rc}")
    return 0 if rc in {0, -15} or once else rc


def main() -> int:
    ap = argparse.ArgumentParser()
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--frame-file", type=Path)
    group.add_argument("--helper", type=Path)
    ap.add_argument("--queue", type=Path)
    ap.add_argument("--pattern")
    ap.add_argument("--stations", default=",".join(sorted(DEFAULT_STATIONS)))
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()
    stations = _parse_stations(args.stations)

    if args.frame_file is not None:
        result = run_frame_file(args.frame_file, stations)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result.get("status") == "PASS" else 1

    if args.queue is None or not args.pattern:
        ap.error("--helper requires --queue and --pattern")
    return run_live_helper(args.helper, args.queue, args.pattern, stations, once=args.once)


if __name__ == "__main__":
    raise SystemExit(main())
