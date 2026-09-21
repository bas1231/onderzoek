#!/usr/bin/env python3
"""A19B: fail-closed prospective MADIS LDM adapter.

Timing semantics are deliberately strict:
- observation_time: timestamp encoded in the meteorological record;
- product_creation_time: LDM data-product metadata creation time;
- ldm_queue_insert_at: LOCAL product-queue insertion time (NOT available from
  pqact PIPE metadata; remains null in A19B-v1);
- adapter_first_seen_at: local CLOCK_REALTIME sampled immediately when this
  handler starts consuming a product;
- adapter_read_complete_at / decode_complete_at: local processing timestamps.

`adapter_first_seen_at` is never called a network receipt timestamp and is never
silently substituted for `ldm_queue_insert_at`.

Live use is intended for a future pqact PIPE action after NOAA supplies the exact
MADIS feedtype/product identifiers. Replay exists only for validation and is
NEVER eligible as prospective latency evidence.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import time
from typing import BinaryIO

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "control" / "weather"))

from madis_omo_public_a19 import DEFAULT_STATIONS, decode_netcdf  # noqa: E402

STATE = Path.home() / ".local" / "state" / "prediction-research"
RAW = STATE / "raw" / "madis_ldm_a19b"
MANIFESTS = STATE / "madis_ldm_manifests"

GZIP_MAGIC = b"\x1f\x8b"
NETCDF3_MAGIC = b"CDF"
HDF5_MAGIC = b"\x89HDF\r\n\x1a\n"
CLOCK_MAX_UNCERTAINTY_MS = 100.0


def _float_seconds(line: str) -> float | None:
    m = re.search(r"([-+]?\d+(?:\.\d+)?)\s+seconds?", line)
    return float(m.group(1)) if m else None


def parse_chronyc_tracking(text: str) -> dict:
    """Parse chronyc tracking into explicit clock-quality evidence.

    `clock_uncertainty_ms` is a conservative derived bound used only as a local
    evidence gate: |system-vs-NTP offset| + root dispersion + root delay/2.
    It is not claimed to be chrony's own formal uncertainty metric.
    """
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip().lower()] = value.strip()

    system_line = fields.get("system time", "")
    system_s = _float_seconds(system_line)
    if system_s is not None:
        if "slow of" in system_line.lower():
            system_s = -abs(system_s)
        elif "fast of" in system_line.lower():
            system_s = abs(system_s)
    root_delay_s = _float_seconds(fields.get("root delay", ""))
    root_disp_s = _float_seconds(fields.get("root dispersion", ""))
    last_offset_s = _float_seconds(fields.get("last offset", ""))
    rms_offset_s = _float_seconds(fields.get("rms offset", ""))
    leap = fields.get("leap status")
    ref_id = fields.get("reference id")
    stratum_raw = fields.get("stratum")
    try:
        stratum = int(stratum_raw) if stratum_raw is not None else None
    except ValueError:
        stratum = None

    system_ms = None if system_s is None else system_s * 1000.0
    root_delay_ms = None if root_delay_s is None else root_delay_s * 1000.0
    root_disp_ms = None if root_disp_s is None else root_disp_s * 1000.0
    uncertainty = None
    if system_ms is not None and root_delay_ms is not None and root_disp_ms is not None:
        uncertainty = abs(system_ms) + root_disp_ms + abs(root_delay_ms) / 2.0

    normal = str(leap or "").strip().lower() == "normal"
    eligible = bool(
        normal
        and uncertainty is not None
        and uncertainty <= CLOCK_MAX_UNCERTAINTY_MS
        and stratum is not None
        and 1 <= stratum <= 15
    )
    return {
        "clock_source": f"chrony:{ref_id}" if ref_id else "chrony",
        "clock_offset_ms": system_ms,
        "clock_uncertainty_ms": uncertainty,
        "clock_uncertainty_semantics": "conservative derived gate = abs(system_offset)+root_dispersion+root_delay/2",
        "last_offset_ms": None if last_offset_s is None else last_offset_s * 1000.0,
        "rms_offset_ms": None if rms_offset_s is None else rms_offset_s * 1000.0,
        "root_delay_ms": root_delay_ms,
        "root_dispersion_ms": root_disp_ms,
        "stratum": stratum,
        "leap_status": leap,
        "evidence_clock_eligible": eligible,
    }


def clock_health() -> dict:
    """Capture clock source/offset/uncertainty; unknown fails closed."""
    if shutil.which("chronyc"):
        try:
            cp = subprocess.run(["chronyc", "tracking", "-n"], text=True, capture_output=True, timeout=3)
            if cp.returncode == 0 and cp.stdout.strip():
                out = parse_chronyc_tracking(cp.stdout)
                out["raw_tracking"] = cp.stdout[-2500:]
                return out
        except Exception as exc:
            chrony_error = f"{type(exc).__name__}: {exc}"
        else:
            chrony_error = f"chronyc_returncode={cp.returncode}"
    else:
        chrony_error = "chronyc_not_found"

    ntp_sync = None
    if shutil.which("timedatectl"):
        try:
            cp = subprocess.run(
                ["timedatectl", "show", "-p", "NTPSynchronized", "--value"],
                text=True,
                capture_output=True,
                timeout=3,
            )
            if cp.returncode == 0:
                raw = cp.stdout.strip().lower()
                ntp_sync = raw == "yes" if raw in {"yes", "no"} else None
        except Exception:
            pass
    return {
        "clock_source": "timedatectl" if ntp_sync is not None else None,
        "clock_offset_ms": None,
        "clock_uncertainty_ms": None,
        "clock_uncertainty_semantics": "unavailable without parsed chrony tracking",
        "ntp_synchronized": ntp_sync,
        "evidence_clock_eligible": False,
        "detail": chrony_error,
    }


def payload_kind(data: bytes) -> str:
    if data.startswith(GZIP_MAGIC):
        return "gzip"
    if data.startswith(NETCDF3_MAGIC):
        return "netcdf3"
    if data.startswith(HDF5_MAGIC):
        return "netcdf4_hdf5"
    return "unknown"


def read_all_with_timing(stream: BinaryIO) -> tuple[bytes, dict]:
    first_wall_ns = time.time_ns()
    first_mono_ns = time.monotonic_ns()
    data = stream.read()
    done_mono_ns = time.monotonic_ns()
    done_wall_ns = time.time_ns()
    return data, {
        "adapter_first_seen_at_ns": first_wall_ns,
        "adapter_first_seen_at": datetime.fromtimestamp(first_wall_ns / 1e9, tz=timezone.utc).isoformat(),
        "adapter_first_seen_monotonic_ns": first_mono_ns,
        "adapter_read_complete_at_ns": done_wall_ns,
        "adapter_read_complete_at": datetime.fromtimestamp(done_wall_ns / 1e9, tz=timezone.utc).isoformat(),
        "adapter_read_complete_monotonic_ns": done_mono_ns,
        "adapter_read_duration_ms": round((done_mono_ns - first_mono_ns) / 1_000_000, 3),
    }


def parse_pqact_metadata_packet(packet: bytes) -> tuple[dict, bytes]:
    """Parse one `pqact PIPE -metadata -close` packet.

    Unidata documents native-host endianness and the field order. We parse the
    dynamic metadata fields and then require the remaining payload length to
    equal the metadata product-size. The documented metadata-length is accepted
    only if it matches either total metadata bytes or metadata bytes excluding
    the initial length word; this avoids guessing that convention.
    """
    if len(packet) < 48:
        raise ValueError("pqact metadata packet too short")
    off = 0

    def take(fmt: str):
        nonlocal off
        size = struct.calcsize(fmt)
        if off + size > len(packet):
            raise ValueError("truncated pqact metadata")
        value = struct.unpack_from(fmt, packet, off)
        off += size
        return value[0] if len(value) == 1 else value

    metadata_length = int(take("=I"))
    if off + 16 > len(packet):
        raise ValueError("truncated signature")
    signature = packet[off:off + 16]
    off += 16
    product_size = int(take("=I"))
    creation_sec = int(take("=Q"))
    creation_usec = int(take("=i"))
    feedtype = int(take("=I"))
    sequence_number = int(take("=I"))
    identifier_len = int(take("=I"))
    if identifier_len < 0 or off + identifier_len > len(packet):
        raise ValueError("invalid identifier length")
    identifier = packet[off:off + identifier_len].decode("utf-8", errors="replace")
    off += identifier_len
    origin_len = int(take("=I"))
    if origin_len < 0 or off + origin_len > len(packet):
        raise ValueError("invalid origin length")
    origin = packet[off:off + origin_len].decode("utf-8", errors="replace")
    off += origin_len

    if metadata_length not in {off, off - 4}:
        raise ValueError(f"metadata length mismatch: declared={metadata_length} parsed={off}")
    payload = packet[off:]
    if len(payload) != product_size:
        raise ValueError(f"product size mismatch: declared={product_size} actual={len(payload)}")
    md5_hex = hashlib.md5(payload).hexdigest()
    if signature.hex() != md5_hex:
        raise ValueError("product signature mismatch")
    if not 0 <= creation_usec < 1_000_000:
        raise ValueError("invalid creation microseconds")
    creation_ns = creation_sec * 1_000_000_000 + creation_usec * 1000
    return ({
        "metadata_length": metadata_length,
        "signature_md5": signature.hex(),
        "product_size": product_size,
        "product_creation_time_ns": creation_ns,
        "product_creation_time": datetime.fromtimestamp(creation_ns / 1e9, tz=timezone.utc).isoformat(),
        "feedtype_numeric": feedtype,
        "sequence_number": sequence_number,
        "product_identifier": identifier,
        "product_origin": origin,
    }, payload)


def observation_latency_summary(decoded: dict, adapter_first_seen_ns: int) -> dict:
    rows = decoded.get("matched_rows") or []
    vals = []
    by_station = {}
    for row in rows:
        try:
            obs_ms = float(row["observation_time_raw"]) * 1000.0
            delta = round(adapter_first_seen_ns / 1_000_000.0 - obs_ms, 3)
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


def archive_and_decode(data: bytes, stations: set[str]) -> tuple[dict, bool]:
    RAW.mkdir(parents=True, exist_ok=True)
    sha = hashlib.sha256(data).hexdigest()
    kind = payload_kind(data)
    raw_path = RAW / f"product-{sha}.bin"
    duplicate = raw_path.exists()
    if not duplicate:
        raw_path.write_bytes(data)

    decoded_bytes = data
    compression = None
    if kind == "gzip":
        compression = "gzip"
        try:
            decoded_bytes = gzip.decompress(data)
        except Exception as exc:
            return ({
                "status": "BLOCKED_GZIP_DECODE",
                "detail": f"{type(exc).__name__}: {exc}",
                "payload_kind": kind,
                "raw_sha256": sha,
                "raw_path": str(raw_path),
            }, duplicate)
        kind = payload_kind(decoded_bytes)

    if kind not in {"netcdf3", "netcdf4_hdf5"}:
        return ({
            "status": "ARCHIVED_UNDECODED",
            "payload_kind": kind,
            "compression": compression,
            "raw_sha256": sha,
            "raw_path": str(raw_path),
        }, duplicate)

    nc_sha = hashlib.sha256(decoded_bytes).hexdigest()
    nc_path = RAW / f"netcdf-{nc_sha}.nc"
    if not nc_path.exists():
        nc_path.write_bytes(decoded_bytes)
    decoded = decode_netcdf(nc_path, stations)
    return ({
        "status": decoded.get("status"),
        "payload_kind": kind,
        "compression": compression,
        "raw_sha256": sha,
        "raw_path": str(raw_path),
        "netcdf_sha256": nc_sha,
        "netcdf_path": str(nc_path),
        "decode": decoded,
    }, duplicate)


def ingest_payload(
    data: bytes,
    timing: dict,
    *,
    mode: str,
    metadata: dict | None,
    stations: set[str],
) -> dict:
    decode_started_ns = time.time_ns()
    decoded_wrapper, duplicate = archive_and_decode(data, stations)
    decode_complete_ns = time.time_ns()
    decoded = decoded_wrapper.get("decode") or {}
    matched = int(decoded.get("matched_station_count") or 0)
    clock = clock_health()
    latency = observation_latency_summary(decoded, int(timing["adapter_first_seen_at_ns"]))

    if not data:
        status = "BLOCKED_EMPTY_PRODUCT"
    elif decoded_wrapper.get("status") == "ARCHIVED_UNDECODED":
        status = "ARCHIVED_UNDECODED"
    elif decoded_wrapper.get("status") != "PASS":
        status = str(decoded_wrapper.get("status") or "BLOCKED_DECODE")
    elif matched == 0:
        status = "NO_REQUESTED_STATIONS_IN_PRODUCT"
    else:
        status = "PASS"

    is_live = mode == "ldm-pipe"
    eligible = bool(
        is_live
        and status == "PASS"
        and not duplicate
        and metadata is not None
        and clock.get("evidence_clock_eligible") is True
    )
    queue_insert_ns = None  # A19B-v1: unavailable from pqact PIPE metadata by design.
    return {
        "schema": "MADIS_LDM_RECEIPT_A19B_V2",
        "task": "WEATHER-MADIS-LDM-RECEIPT-A19B",
        "status": status,
        "mode": mode,
        "bytes": len(data),
        **timing,
        "decode_started_at_ns": decode_started_ns,
        "decode_complete_at_ns": decode_complete_ns,
        "decode_complete_at": datetime.fromtimestamp(decode_complete_ns / 1e9, tz=timezone.utc).isoformat(),
        "ldm_queue_insert_at_ns": queue_insert_ns,
        "ldm_queue_insert_at": None,
        "ldm_queue_insert_source": "UNAVAILABLE_FROM_PQACT_PIPE_METADATA_A19B_V1",
        "product_metadata": metadata,
        "clock_health": clock,
        "adapter_timestamp_semantics": "adapter_first_seen_at is local handler time; NOT network receipt and NOT LDM queue insertion",
        "queue_timestamp_semantics": "true local LDM queue insertion must come from queue-native evidence (PQ API/cursor) in A19B-v2",
        "observation_to_adapter_first_seen": latency,
        "queue_insert_to_adapter_first_seen_ms": None,
        "duplicate_product": duplicate,
        "eligible_for_prospective_latency_analysis": eligible,
        "eligibility_guard": "Requires live pqact metadata, decoded requested stations, unique product, and chrony evidence within clock uncertainty gate. Queue-insertion claims remain unavailable in v1.",
        "station_set_guard": "Requested stations are research inputs; current Kalshi/TWC contributor configuration must be independently versioned.",
        "economic_conclusion": "NO_PROVEN_EDGE",
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
    }


def write_manifest(result: dict) -> Path:
    MANIFESTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    sha_short = str((result.get("decode") or {}).get("raw_sha256") or "nohash")[:12]
    path = MANIFESTS / f"madis-ldm-a19b-{stamp}-{sha_short}.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--file", type=Path, help="replay raw/gz/netCDF payload; never live latency evidence")
    src.add_argument("--pqact-metadata-stdin", action="store_true", help="read one pqact PIPE -metadata -close packet from stdin")
    ap.add_argument("--stations", default=",".join(DEFAULT_STATIONS))
    args = ap.parse_args()

    stations = {x.strip().upper() for x in args.stations.split(",") if x.strip()}
    if args.file:
        with args.file.open("rb") as f:
            data, timing = read_all_with_timing(f)
        mode = "replay"
        metadata = None
    else:
        packet, timing = read_all_with_timing(sys.stdin.buffer)
        mode = "ldm-pipe"
        try:
            metadata, data = parse_pqact_metadata_packet(packet)
        except Exception as exc:
            result = {
                "schema": "MADIS_LDM_RECEIPT_A19B_V2",
                "task": "WEATHER-MADIS-LDM-RECEIPT-A19B",
                "status": "BLOCKED_PQACT_METADATA_PARSE",
                "mode": mode,
                **timing,
                "detail": f"{type(exc).__name__}: {exc}",
                "ldm_queue_insert_at_ns": None,
                "ldm_queue_insert_at": None,
                "ldm_queue_insert_source": "UNAVAILABLE_FROM_PQACT_PIPE_METADATA_A19B_V1",
                "eligible_for_prospective_latency_analysis": False,
                "economic_conclusion": "NO_PROVEN_EDGE",
                "live_trading": False,
                "paid_action": False,
                "wallet_action": False,
            }
            manifest = write_manifest(result)
            result["manifest"] = str(manifest)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 2

    result = ingest_payload(data, timing, mode=mode, metadata=metadata, stations=stations)
    manifest = write_manifest(result)
    result["manifest"] = str(manifest)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] in {"PASS", "NO_REQUESTED_STATIONS_IN_PRODUCT", "ARCHIVED_UNDECODED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
