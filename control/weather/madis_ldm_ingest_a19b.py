#!/usr/bin/env python3
"""A19B: fail-closed receipt adapter for prospective NOAA MADIS LDM products.

The adapter is deliberately agnostic to MADIS feedtype/product identifiers until
NOAA supplies the user's actual LDM configuration. It can be called from a future
pqact PIPE action. The first local wall-clock and monotonic timestamps are taken
before reading product bytes from stdin.

Replay mode exists only to validate the decoder. Replay timestamps are NEVER
eligible as live latency evidence.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
from pathlib import Path
import shutil
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


def clock_sync_status() -> dict:
    """Best-effort clock-sync evidence; unknown fails closed for absolute latency."""
    if shutil.which("timedatectl"):
        try:
            cp = subprocess.run(
                ["timedatectl", "show", "-p", "NTPSynchronized", "--value"],
                text=True,
                capture_output=True,
                timeout=3,
            )
            value = cp.stdout.strip().lower()
            if cp.returncode == 0 and value in {"yes", "no"}:
                return {"source": "timedatectl", "synchronized": value == "yes", "raw": value}
        except Exception:
            pass
    if shutil.which("chronyc"):
        try:
            cp = subprocess.run(["chronyc", "tracking"], text=True, capture_output=True, timeout=3)
            text = cp.stdout.strip()
            if cp.returncode == 0 and text:
                # chronyc returning a valid tracking block proves a running clock discipline
                # source, but we still avoid inventing an offset threshold here.
                return {"source": "chronyc", "synchronized": None, "raw": text[-1500:]}
        except Exception:
            pass
    return {"source": None, "synchronized": None, "raw": None}


def payload_kind(data: bytes) -> str:
    if data.startswith(GZIP_MAGIC):
        return "gzip"
    if data.startswith(NETCDF3_MAGIC):
        return "netcdf3"
    if data.startswith(HDF5_MAGIC):
        return "netcdf4_hdf5"
    return "unknown"


def read_product(stream: BinaryIO) -> tuple[bytes, dict]:
    receipt_wall_start_ns = time.time_ns()
    receipt_mono_start_ns = time.monotonic_ns()
    data = stream.read()
    receipt_mono_end_ns = time.monotonic_ns()
    receipt_wall_end_ns = time.time_ns()
    return data, {
        "receipt_wall_start_ns": receipt_wall_start_ns,
        "receipt_wall_end_ns": receipt_wall_end_ns,
        "receipt_monotonic_start_ns": receipt_mono_start_ns,
        "receipt_monotonic_end_ns": receipt_mono_end_ns,
        "read_duration_ms": round((receipt_mono_end_ns - receipt_mono_start_ns) / 1_000_000, 3),
    }


def observation_latency_summary(decoded: dict, receipt_wall_start_ns: int) -> dict:
    rows = decoded.get("matched_rows") or []
    vals = []
    by_station = {}
    for row in rows:
        try:
            obs_ms = float(row["observation_time_raw"]) * 1000.0
            delta = round(receipt_wall_start_ns / 1_000_000.0 - obs_ms, 3)
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


def archive_and_decode(data: bytes, stations: set[str]) -> tuple[dict, Path | None]:
    RAW.mkdir(parents=True, exist_ok=True)
    sha = hashlib.sha256(data).hexdigest()
    kind = payload_kind(data)
    raw_path = RAW / f"product-{sha}.bin"
    if not raw_path.exists():
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
            }, None)
        kind = payload_kind(decoded_bytes)

    if kind not in {"netcdf3", "netcdf4_hdf5"}:
        return ({
            "status": "ARCHIVED_UNDECODED",
            "payload_kind": kind,
            "compression": compression,
            "raw_sha256": sha,
            "raw_path": str(raw_path),
        }, None)

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
    }, nc_path)


def ingest(data: bytes, timing: dict, *, mode: str, product_id: str | None, feedtype: str | None, stations: set[str]) -> dict:
    decoded_wrapper, _ = archive_and_decode(data, stations)
    decoded = decoded_wrapper.get("decode") or {}
    matched = int(decoded.get("matched_station_count") or 0)
    clock = clock_sync_status()
    latency = observation_latency_summary(decoded, int(timing["receipt_wall_start_ns"]))

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
    eligible = bool(is_live and status == "PASS" and clock.get("synchronized") is True)
    return {
        "schema": "MADIS_LDM_RECEIPT_A19B_V1",
        "task": "WEATHER-MADIS-LDM-RECEIPT-A19B",
        "status": status,
        "mode": mode,
        "product_id": product_id,
        "feedtype": feedtype,
        "bytes": len(data),
        **timing,
        "clock_sync": clock,
        "receipt_semantics": (
            "pqact child process timestamp taken immediately before stdin read"
            if is_live else
            "replay/file timestamp; never use as prospective latency evidence"
        ),
        "decode": decoded_wrapper,
        "observation_to_local_receipt": latency,
        "eligible_for_prospective_latency_analysis": eligible,
        "eligibility_guard": (
            "Requires mode=ldm-pipe, decoded requested stations, and positive local NTP synchronization evidence."
        ),
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
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--file", type=Path, help="replay a captured product; not live evidence")
    ap.add_argument("--mode", choices=("replay", "ldm-pipe"), default="replay")
    ap.add_argument("--product-id")
    ap.add_argument("--feedtype")
    ap.add_argument("--stations", default=",".join(DEFAULT_STATIONS))
    args = ap.parse_args()

    stations = {x.strip().upper() for x in args.stations.split(",") if x.strip()}
    if args.file:
        # Explicitly force replay semantics even if --mode was mistakenly supplied.
        with args.file.open("rb") as f:
            data, timing = read_product(f)
        mode = "replay"
    else:
        data, timing = read_product(sys.stdin.buffer)
        mode = args.mode

    result = ingest(
        data,
        timing,
        mode=mode,
        product_id=args.product_id,
        feedtype=args.feedtype,
        stations=stations,
    )
    manifest = write_manifest(result)
    result["manifest"] = str(manifest)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] in {"PASS", "NO_REQUESTED_STATIONS_IN_PRODUCT", "ARCHIVED_UNDECODED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
