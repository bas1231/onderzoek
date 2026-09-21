#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile

from a19a_proven_replay_fixture import select_proven_a19a_gzip


def write_manifest(root: Path, stamp: str, latest_file: str, payload: bytes, *, full: bool = True, wrong_sha: bool = False):
    sha = hashlib.sha256(payload).hexdigest()
    stored_sha = ("0" * 64) if wrong_sha else sha
    raw = root / "raw"
    mans = root / "manifests"
    raw.mkdir(parents=True, exist_ok=True)
    mans.mkdir(parents=True, exist_ok=True)
    gz = raw / f"{latest_file[:-3]}-{stored_sha}.gz"
    gz.write_bytes(payload)
    obj = {
        "status": "PASS",
        "latest_file": latest_file,
        "compressed_sha256": stored_sha,
        "decode": {
            "status": "PASS" if full else "PARTIAL_REQUESTED_STATION_MATCH",
            "matched_station_count": 5 if full else 4,
            "matched_stations": ["KFLL", "KFXE", "KMIA", "KOPF", "KPMP"] if full else ["KFLL", "KFXE", "KMIA", "KOPF"],
            "requested_stations": ["KFLL", "KFXE", "KMIA", "KOPF", "KPMP"],
            "requested_station_coverage_fraction": 1.0 if full else 0.8,
        },
    }
    (mans / f"madis-omo-a19a-{stamp}.json").write_text(json.dumps(obj), encoding="utf-8")
    return raw, mans, gz


def test_newest_full_pass_is_selected_not_newest_partial():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        raw, mans, older = write_manifest(root, "20260921T180000.000000Z", "20260921_1700.gz", b"older-full", full=True)
        write_manifest(root, "20260921T180100.000000Z", "20260921_1800.gz", b"newer-partial", full=False)
        out = select_proven_a19a_gzip(raw, mans)
        assert out["status"] == "PASS"
        assert Path(out["gzip_path"]) == older
        assert out["latest_file"] == "20260921_1700.gz"


def test_digest_mismatch_is_rejected_and_older_good_fixture_used():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        raw, mans, older = write_manifest(root, "20260921T180000.000000Z", "20260921_1700.gz", b"good", full=True)
        _, _, bad = write_manifest(root, "20260921T180100.000000Z", "20260921_1800.gz", b"bad", full=True)
        bad.write_bytes(b"tampered")
        out = select_proven_a19a_gzip(raw, mans)
        assert out["status"] == "PASS"
        assert Path(out["gzip_path"]) == older
        assert any(x["reason"] == "gzip_sha256_mismatch" for x in out["rejected_newer_candidates"])


def test_no_full_pass_fails_closed():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        raw, mans, _ = write_manifest(root, "20260921T180000.000000Z", "20260921_1700.gz", b"partial", full=False)
        out = select_proven_a19a_gzip(raw, mans)
        assert out["status"] == "NO_PROVEN_A19A_FIXTURE"


if __name__ == "__main__":
    tests = [
        test_newest_full_pass_is_selected_not_newest_partial,
        test_digest_mismatch_is_rejected_and_older_good_fixture_used,
        test_no_full_pass_fails_closed,
    ]
    for test in tests:
        test()
    print(f"A19A_PROVEN_REPLAY_FIXTURE_TESTS_PASS {len(tests)}")
