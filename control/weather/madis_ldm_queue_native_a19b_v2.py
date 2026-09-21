#!/usr/bin/env python3
"""A19B-v2: queue-native MADIS LDM timing adapter.

This module consumes a small binary framing protocol emitted by
`madis_ldm_queue_reader_a19b_v2.c`.  The C reader uses the LDM product-queue
API `pq_next()` and takes the queue insertion timestamp directly from
`queue_par_t.inserted`.

Timing semantics are intentionally strict:
- observation_time: timestamp inside the meteorological record;
- product_metadata_time: `prod_info.arrival` supplied by LDM product metadata;
- ldm_queue_insert_at: local LDM product-queue insertion time from
  `queue_par_t.inserted`;
- queue_reader_callback_at: CLOCK_REALTIME sampled in the C callback;
- python_frame_received_at: local time after the full helper frame is read;
- decode_complete_at: local time after archive + meteorological decode.

Only a real helper process reading a real LDM product queue can set
`eligible_for_queue_insertion_latency_analysis=True`.  Frame-file replay is
always ineligible, even if every timestamp and decode is otherwise valid.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
import sys
import time
from typing import BinaryIO

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control" / "weather"))

from madis_omo_public_a19 import DEFAULT_STATIONS  # noqa: E402
from madis_ldm_ingest_a19b import (  # noqa: E402
    archive_and_decode,
    clock_health,
    observation_latency_summary,
)

STATE = Path.home() / ".local" / "state" / "prediction-research"
EVIDENCE_DIR = STATE / "madis_ldm_queue_native_a19b_v2"

MAGIC = b"A19BQV2\0"
FRAME_VERSION = 1
MAX_PRODUCT_BYTES = 256 * 1024 * 1024
MAX_TEXT_BYTES = 16 * 1024
FLAG_EARLY_CURSOR = 1 << 0
FLAG_QUEUE_FULL = 1 << 1
FLAG_PRODUCT_LOCKED = 1 << 2

# magic, version, flags, payload_len,
# queue sec/usec, prod_info.arrival sec/usec,
# callback realtime sec/nsec, callback monotonic sec/nsec,
# feedtype, seqno, info_size, ident_len, origin_len, signature[16]
PREFIX = struct.Struct(">8sIIQqiqiqiqiIIIII16s")


@dataclass(frozen=True)
class QueueFrame:
    payload: bytes
    flags: int
    queue_insert_at_ns: int
    product_metadata_time_ns: int
    callback_realtime_ns: int
    callback_monotonic_ns: int
    feedtype_numeric: int
    sequence_number: int
    product_identifier: str
    product_origin: str
    ldm_signature_hex: str
    product_info_size: int

    @property
    def queue_insert_to_callback_ms(self) -> float:
        return round((self.callback_realtime_ns - self.queue_insert_at_ns) / 1_000_000.0, 3)


def _iso(ns: int) -> str:
    return datetime.fromtimestamp(ns / 1e9, tz=timezone.utc).isoformat()


def _read_exact(stream: BinaryIO, n: int) -> bytes:
    chunks: list[bytes] = []
    remaining = n
    while remaining:
        chunk = stream.read(remaining)
        if not chunk:
            raise EOFError(f"truncated frame: wanted {n} bytes, missing {remaining}")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def read_frame(stream: BinaryIO) -> QueueFrame | None:
    """Read and validate one queue-native frame.

    A clean EOF before a new prefix returns None.  Any partial/malformed frame
    raises, so callers cannot silently accept damaged timing evidence.
    """
    first = stream.read(1)
    if first == b"":
        return None
    prefix_bytes = first + _read_exact(stream, PREFIX.size - 1)
    (
        magic,
        version,
        flags,
        payload_len,
        queue_sec,
        queue_usec,
        product_sec,
        product_usec,
        callback_rt_sec,
        callback_rt_nsec,
        callback_mono_sec,
        callback_mono_nsec,
        feedtype,
        seqno,
        info_size,
        ident_len,
        origin_len,
        signature,
    ) = PREFIX.unpack(prefix_bytes)

    if magic != MAGIC:
        raise ValueError("queue-native frame magic mismatch")
    if version != FRAME_VERSION:
        raise ValueError(f"unsupported queue-native frame version: {version}")
    if payload_len > MAX_PRODUCT_BYTES:
        raise ValueError("queue-native payload exceeds safety limit")
    if info_size != payload_len:
        raise ValueError(f"prod_info size mismatch: info={info_size} frame={payload_len}")
    if ident_len > MAX_TEXT_BYTES or origin_len > MAX_TEXT_BYTES:
        raise ValueError("queue-native metadata string exceeds safety limit")
    if not 0 <= queue_usec < 1_000_000:
        raise ValueError("invalid queue insertion microseconds")
    if not 0 <= product_usec < 1_000_000:
        raise ValueError("invalid product metadata microseconds")
    if not 0 <= callback_rt_nsec < 1_000_000_000:
        raise ValueError("invalid callback realtime nanoseconds")
    if not 0 <= callback_mono_nsec < 1_000_000_000:
        raise ValueError("invalid callback monotonic nanoseconds")
    if queue_sec <= 0 or callback_rt_sec <= 0 or callback_mono_sec < 0:
        raise ValueError("invalid non-positive timing field")

    ident_raw = _read_exact(stream, int(ident_len))
    origin_raw = _read_exact(stream, int(origin_len))
    try:
        ident = ident_raw.decode("utf-8", errors="strict")
        origin = origin_raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("queue-native metadata is not valid UTF-8") from exc
    payload = _read_exact(stream, int(payload_len))

    queue_ns = int(queue_sec) * 1_000_000_000 + int(queue_usec) * 1000
    product_ns = int(product_sec) * 1_000_000_000 + int(product_usec) * 1000
    callback_rt_ns = int(callback_rt_sec) * 1_000_000_000 + int(callback_rt_nsec)
    callback_mono_ns = int(callback_mono_sec) * 1_000_000_000 + int(callback_mono_nsec)

    if queue_ns > callback_rt_ns:
        raise ValueError("queue insertion timestamp is after queue-reader callback")

    return QueueFrame(
        payload=payload,
        flags=int(flags),
        queue_insert_at_ns=queue_ns,
        product_metadata_time_ns=product_ns,
        callback_realtime_ns=callback_rt_ns,
        callback_monotonic_ns=callback_mono_ns,
        feedtype_numeric=int(feedtype),
        sequence_number=int(seqno),
        product_identifier=ident,
        product_origin=origin,
        ldm_signature_hex=signature.hex(),
        product_info_size=int(info_size),
    )


def build_test_frame(
    payload: bytes,
    *,
    queue_insert_at_ns: int | None = None,
    product_metadata_time_ns: int | None = None,
    callback_realtime_ns: int | None = None,
    callback_monotonic_ns: int = 123_000_000_000,
    feedtype_numeric: int = 7,
    sequence_number: int = 42,
    product_identifier: str = "TEST-HF-ASOS",
    product_origin: str = "test-origin",
    flags: int = 0,
    payload_len_override: int | None = None,
    info_size_override: int | None = None,
    version: int = FRAME_VERSION,
    signature: bytes | None = None,
) -> bytes:
    """Create a deterministic frame for tests/replay only."""
    now = time.time_ns()
    queue_ns = int(queue_insert_at_ns if queue_insert_at_ns is not None else now - 5_000_000)
    callback_ns = int(callback_realtime_ns if callback_realtime_ns is not None else now)
    product_ns = int(product_metadata_time_ns if product_metadata_time_ns is not None else queue_ns - 1_000_000)
    ident = product_identifier.encode("utf-8")
    origin = product_origin.encode("utf-8")
    sig = signature if signature is not None else hashlib.md5(payload).digest()
    if len(sig) != 16:
        raise ValueError("test signature must be 16 bytes")
    payload_len = len(payload) if payload_len_override is None else int(payload_len_override)
    info_size = len(payload) if info_size_override is None else int(info_size_override)

    def sec_sub(ns: int, subscale: int) -> tuple[int, int]:
        return divmod(ns, 1_000_000_000)[0], (ns % 1_000_000_000) // subscale

    queue_sec, queue_usec = sec_sub(queue_ns, 1000)
    product_sec, product_usec = sec_sub(product_ns, 1000)
    callback_sec, callback_nsec = divmod(callback_ns, 1_000_000_000)
    callback_mono_sec, callback_mono_nsec = divmod(callback_monotonic_ns, 1_000_000_000)
    prefix = PREFIX.pack(
        MAGIC,
        int(version),
        int(flags),
        int(payload_len),
        int(queue_sec),
        int(queue_usec),
        int(product_sec),
        int(product_usec),
        int(callback_sec),
        int(callback_nsec),
        int(callback_mono_sec),
        int(callback_mono_nsec),
        int(feedtype_numeric),
        int(sequence_number),
        int(info_size),
        len(ident),
        len(origin),
        sig,
    )
    return prefix + ident + origin + payload


def _latency_from_rows(decoded: dict, target_ns: int) -> dict:
    rows = decoded.get("matched_rows") or []
    vals: list[float] = []
    by_station: dict[str, float] = {}
    for row in rows:
        try:
            obs_ms = float(row["observation_time_raw"]) * 1000.0
            delta = round(target_ns / 1_000_000.0 - obs_ms, 3)
            vals.append(delta)
            by_station[str(row.get("station"))] = delta
        except Exception:
            continue
    if not vals:
        return {"n": 0, "min_ms": None, "max_ms": None, "by_station_ms": by_station}
    return {
        "n": len(vals),
        "min_ms": min(vals),
        "max_ms": max(vals),
        "by_station_ms": dict(sorted(by_station.items())),
    }


def ingest_frame(frame: QueueFrame, *, mode: str, stations: set[str]) -> dict:
    """Archive/decode a validated frame and apply evidence gates."""
    python_received_ns = time.time_ns()
    decode_started_ns = time.time_ns()
    decoded_wrapper, duplicate = archive_and_decode(frame.payload, stations)
    decode_complete_ns = time.time_ns()
    decoded = decoded_wrapper.get("decode") or {}
    matched = int(decoded.get("matched_station_count") or 0)
    clock = clock_health()

    if not frame.payload:
        status = "BLOCKED_EMPTY_PRODUCT"
    elif decoded_wrapper.get("status") == "ARCHIVED_UNDECODED":
        status = "ARCHIVED_UNDECODED"
    elif decoded_wrapper.get("status") != "PASS":
        status = str(decoded_wrapper.get("status") or "BLOCKED_DECODE")
    elif matched == 0:
        status = "NO_REQUESTED_STATIONS_IN_PRODUCT"
    else:
        status = "PASS"

    live_queue_native = mode == "ldm-queue-native"
    queue_lag_ms = frame.queue_insert_to_callback_ms
    callback_to_python_ms = round((python_received_ns - frame.callback_realtime_ns) / 1_000_000.0, 3)
    if callback_to_python_ms < 0:
        status = "BLOCKED_CALLBACK_AFTER_PYTHON_RECEIVE"

    queue_eligible = bool(
        live_queue_native
        and status == "PASS"
        and not duplicate
        and queue_lag_ms >= 0
        and callback_to_python_ms >= 0
        and clock.get("evidence_clock_eligible") is True
    )
    adapter_eligible = bool(
        live_queue_native
        and status == "PASS"
        and not duplicate
        and callback_to_python_ms >= 0
        and clock.get("evidence_clock_eligible") is True
    )

    return {
        "schema": "MADIS_LDM_QUEUE_NATIVE_A19B_V2",
        "task": "WEATHER-MADIS-LDM-QUEUE-NATIVE-A19B-V2",
        "status": status,
        "mode": mode,
        "bytes": len(frame.payload),
        "raw_payload_sha256": hashlib.sha256(frame.payload).hexdigest(),
        "ldm_signature_hex": frame.ldm_signature_hex,
        "ldm_queue_insert_at_ns": frame.queue_insert_at_ns,
        "ldm_queue_insert_at": _iso(frame.queue_insert_at_ns),
        "ldm_queue_insert_source": "LDM_PQ_NEXT_QUEUE_PAR_T_INSERTED",
        "queue_timestamp_semantics": "local LDM product-queue insertion time from pq_next() queue_par_t.inserted",
        "product_metadata_time_ns": frame.product_metadata_time_ns,
        "product_metadata_time": _iso(frame.product_metadata_time_ns),
        "product_metadata_time_semantics": "LDM prod_info.arrival metadata; NOT local queue insertion time",
        "queue_reader_callback_at_ns": frame.callback_realtime_ns,
        "queue_reader_callback_at": _iso(frame.callback_realtime_ns),
        "queue_reader_callback_monotonic_ns": frame.callback_monotonic_ns,
        "python_frame_received_at_ns": python_received_ns,
        "python_frame_received_at": _iso(python_received_ns),
        "decode_started_at_ns": decode_started_ns,
        "decode_complete_at_ns": decode_complete_ns,
        "decode_complete_at": _iso(decode_complete_ns),
        "queue_insert_to_reader_callback_ms": queue_lag_ms,
        "reader_callback_to_python_frame_ms": callback_to_python_ms,
        "queue_insert_to_python_frame_ms": round((python_received_ns - frame.queue_insert_at_ns) / 1_000_000.0, 3),
        "product_metadata_to_queue_insert_ms": round((frame.queue_insert_at_ns - frame.product_metadata_time_ns) / 1_000_000.0, 3),
        "feedtype_numeric": frame.feedtype_numeric,
        "sequence_number": frame.sequence_number,
        "product_identifier": frame.product_identifier,
        "product_origin": frame.product_origin,
        "queue_flags": {
            "early_cursor": bool(frame.flags & FLAG_EARLY_CURSOR),
            "queue_full": bool(frame.flags & FLAG_QUEUE_FULL),
            "product_locked": bool(frame.flags & FLAG_PRODUCT_LOCKED),
        },
        "clock_health": clock,
        "decode": decoded_wrapper,
        "duplicate_raw_product": duplicate,
        "observation_to_queue_insert": _latency_from_rows(decoded, frame.queue_insert_at_ns),
        "observation_to_reader_callback": observation_latency_summary(decoded, frame.callback_realtime_ns),
        "eligible_for_adapter_first_seen_latency_analysis": adapter_eligible,
        "eligible_for_queue_insertion_latency_analysis": queue_eligible,
        "queue_evidence_semantics": "eligibility requires real queue-native mode, nonduplicate decoded product, nonnegative timing, and eligible local clock evidence",
        "economic_conclusion": "NO_PROVEN_EDGE",
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
    }


def persist_evidence(result: dict) -> Path:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    sha = str(result.get("raw_payload_sha256") or "unknown")
    insert_ns = str(result.get("ldm_queue_insert_at_ns") or "unknown")
    path = EVIDENCE_DIR / f"event-{insert_ns}-{sha}.json"
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != encoded:
            raise RuntimeError("immutable queue-native evidence collision")
    else:
        path.write_text(encoded, encoding="utf-8")
    return path


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
