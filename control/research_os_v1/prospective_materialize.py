from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .prospective_collector import safe_cycle_filename


def _load_object(path: Path) -> dict[str, Any]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid_raw_telemetry_json:{path}:{type(exc).__name__}") from exc
    if not isinstance(obj, dict):
        raise ValueError(f"raw_telemetry_object_required:{path}")
    return obj


def _metadata_map(cohort_status: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if not isinstance(cohort_status, dict) or cohort_status.get("cohort_frozen") is not True:
        raise ValueError("cohort_not_frozen")
    rows = cohort_status.get("cohort_case_metadata")
    if not isinstance(rows, list):
        raise ValueError("cohort_case_metadata_missing")
    out: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"cohort_metadata_row_invalid:{index}")
        case_id = row.get("case_id")
        hour = row.get("active_hour_id")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError(f"cohort_case_id_invalid:{index}")
        if not isinstance(hour, str) or not hour.strip():
            raise ValueError(f"cohort_active_hour_invalid:{case_id}")
        if case_id in out:
            raise ValueError(f"duplicate_cohort_case_id:{case_id}")
        out[case_id] = row
    return out


def _load_side_cycle(collection_dir: Path, side: str, active_hour_id: str) -> dict[str, Any]:
    filename = safe_cycle_filename(active_hour_id)
    path = collection_dir / "raw_telemetry" / side.lower() / filename
    if not path.exists():
        raise ValueError(f"raw_telemetry_missing:{side}:{active_hour_id}")
    obj = _load_object(path)
    if obj.get("schema_version") != 1:
        raise ValueError(f"raw_telemetry_schema_mismatch:{side}:{active_hour_id}")
    if obj.get("side") != side:
        raise ValueError(f"raw_telemetry_side_mismatch:{side}:{active_hour_id}")
    if obj.get("run_id") != active_hour_id:
        raise ValueError(f"raw_telemetry_run_id_mismatch:{side}:{active_hour_id}")
    if obj.get("economic_conclusion") != "NO_PROVEN_EDGE":
        raise ValueError(f"raw_telemetry_economic_conclusion_invalid:{side}:{active_hour_id}")
    records = obj.get("records")
    if not isinstance(records, list):
        raise ValueError(f"raw_telemetry_records_missing:{side}:{active_hour_id}")
    return obj


def materialize_observation_inputs(
    collection_dir: Path,
    cohort_status: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    metadata = _metadata_map(cohort_status)
    cohort_hash = cohort_status.get("cohort_hash")
    if not isinstance(cohort_hash, str) or not cohort_hash.strip():
        raise ValueError("cohort_hash_required")

    hours = sorted({row["active_hour_id"] for row in metadata.values()})
    side_cache: dict[tuple[str, str], dict[str, Any]] = {}
    for side in ("BASELINE", "CHALLENGER"):
        for hour in hours:
            side_cache[(side, hour)] = _load_side_cycle(collection_dir, side, hour)

    output: dict[str, list[dict[str, Any]]] = {"BASELINE": [], "CHALLENGER": []}
    for side in ("BASELINE", "CHALLENGER"):
        seen: set[str] = set()
        for case_id in sorted(metadata):
            hour = metadata[case_id]["active_hour_id"]
            payload = side_cache[(side, hour)]
            matches = [
                row
                for row in payload["records"]
                if isinstance(row, dict) and row.get("case_id") == case_id
            ]
            if len(matches) != 1:
                raise ValueError(
                    f"raw_case_match_count:{side}:{case_id}:{len(matches)}"
                )
            if case_id in seen:
                raise ValueError(f"duplicate_materialized_case:{side}:{case_id}")
            seen.add(case_id)
            output[side].append(matches[0])
        if seen != set(metadata):
            raise ValueError(f"materialized_case_set_mismatch:{side}")

    baseline = {
        "schema_version": 1,
        "side": "BASELINE",
        "cohort_hash": cohort_hash,
        "records": output["BASELINE"],
    }
    challenger = {
        "schema_version": 1,
        "side": "CHALLENGER",
        "cohort_hash": cohort_hash,
        "records": output["CHALLENGER"],
    }
    return baseline, challenger
