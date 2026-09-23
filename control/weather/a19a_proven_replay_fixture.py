#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable


def _valid_manifest(obj: object, expected_station_count: int) -> bool:
    if not isinstance(obj, dict):
        return False
    decode = obj.get("decode")
    if not isinstance(decode, dict):
        return False
    try:
        count = int(decode.get("matched_station_count"))
        coverage = float(decode.get("requested_station_coverage_fraction"))
    except (TypeError, ValueError):
        return False
    requested = decode.get("requested_stations")
    matched = decode.get("matched_stations")
    return bool(
        obj.get("status") == "PASS"
        and decode.get("status") == "PASS"
        and count == expected_station_count
        and coverage == 1.0
        and isinstance(requested, list)
        and len(requested) == expected_station_count
        and isinstance(matched, list)
        and len(matched) == expected_station_count
        and isinstance(obj.get("latest_file"), str)
        and str(obj.get("latest_file")).endswith(".gz")
        and isinstance(obj.get("compressed_sha256"), str)
        and len(str(obj.get("compressed_sha256"))) == 64
    )


def select_proven_a19a_gzip(
    raw_dir: Path,
    manifest_dir: Path,
    *,
    expected_station_count: int = 5,
) -> dict:
    """Return newest manifest-proven immutable A19A gzip, or fail closed.

    Newest is defined by the manifest filename timestamp, not filesystem mtime.
    A candidate must prove a complete requested-station decode and its archived
    gzip bytes must still match the manifest's compressed SHA-256.
    """
    if not raw_dir.is_dir() or not manifest_dir.is_dir():
        return {"status": "NO_PROVEN_A19A_FIXTURE"}

    manifests: Iterable[Path] = reversed(sorted(manifest_dir.glob("madis-omo-a19a-*.json")))
    rejected: list[dict] = []
    for manifest in manifests:
        try:
            obj = json.loads(manifest.read_text(encoding="utf-8"))
        except Exception as exc:
            rejected.append({"manifest": str(manifest), "reason": f"manifest_parse:{type(exc).__name__}"})
            continue
        if not _valid_manifest(obj, expected_station_count):
            rejected.append({"manifest": str(manifest), "reason": "manifest_not_full_pass"})
            continue

        latest_file = str(obj["latest_file"])
        sha = str(obj["compressed_sha256"]).lower()
        base = latest_file[:-3]
        gz = raw_dir / f"{base}-{sha}.gz"
        if not gz.is_file():
            rejected.append({"manifest": str(manifest), "reason": "archived_gzip_missing", "expected": str(gz)})
            continue
        try:
            actual_sha = hashlib.sha256(gz.read_bytes()).hexdigest()
        except Exception as exc:
            rejected.append({"manifest": str(manifest), "reason": f"gzip_read:{type(exc).__name__}"})
            continue
        if actual_sha != sha:
            rejected.append({"manifest": str(manifest), "reason": "gzip_sha256_mismatch", "expected_sha256": sha, "actual_sha256": actual_sha})
            continue

        decode = obj["decode"]
        return {
            "status": "PASS",
            "gzip_path": str(gz),
            "manifest_path": str(manifest),
            "compressed_sha256": sha,
            "latest_file": latest_file,
            "matched_station_count": int(decode["matched_station_count"]),
            "matched_stations": list(decode["matched_stations"]),
            "requested_station_coverage_fraction": float(decode["requested_station_coverage_fraction"]),
            "selection_semantics": "newest immutable manifest-proven full-station A19A decode; never raw-directory latest-by-mtime",
            "rejected_newer_candidates": rejected[:20],
        }

    return {
        "status": "NO_PROVEN_A19A_FIXTURE",
        "rejected_candidates": rejected[:50],
    }
