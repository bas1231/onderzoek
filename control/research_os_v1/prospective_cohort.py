from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .prospective_collector import validate_cycle_capture
from .prospective_resolver import resolve_case


_HOUR_RE = re.compile(r"^hourly-(\d{8}T\d{6})([+-]\d{4})$")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _hour_sort_key(active_hour_id: str) -> datetime:
    if not isinstance(active_hour_id, str):
        raise ValueError("active_hour_id_must_be_string")
    match = _HOUR_RE.fullmatch(active_hour_id.strip())
    if not match:
        raise ValueError(f"invalid_active_hour_id:{active_hour_id}")
    return datetime.strptime("".join(match.groups()), "%Y%m%dT%H%M%S%z")


def load_cycle_directory(root: Path) -> list[dict[str, Any]]:
    cycles_dir = Path(root) / "cycles"
    if not cycles_dir.exists() or not cycles_dir.is_dir():
        return []
    cycles: list[dict[str, Any]] = []
    for path in sorted(cycles_dir.glob("*.json")):
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ValueError(f"invalid_cycle_json:{path}:{type(exc).__name__}") from exc
        if not isinstance(obj, dict):
            raise ValueError(f"cycle_object_required:{path}")
        errors = validate_cycle_capture(obj)
        if errors:
            raise ValueError(f"invalid_cycle:{path}:" + ",".join(errors))
        cycles.append(obj)
    return cycles


def _validate_and_sort_cycles(cycles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(cycles, list):
        raise ValueError("cycles_must_be_list")
    rows: list[dict[str, Any]] = []
    seen_hours: set[str] = set()
    seen_case_ids: set[str] = set()
    for cycle in cycles:
        errors = validate_cycle_capture(cycle)
        if errors:
            raise ValueError("invalid_cycle:" + ",".join(errors))
        hour = cycle["active_hour_id"]
        _hour_sort_key(hour)
        if hour in seen_hours:
            raise ValueError(f"duplicate_active_hour:{hour}")
        seen_hours.add(hour)
        for case in cycle["cases"]:
            case_id = case["case_id"]
            if case_id in seen_case_ids:
                raise ValueError(f"duplicate_case_across_cycles:{case_id}")
            seen_case_ids.add(case_id)
        rows.append(cycle)
    return sorted(rows, key=lambda row: _hour_sort_key(row["active_hour_id"]))


def _cohort_cutoff(cycles: list[dict[str, Any]]) -> int | None:
    case_count = 0
    shapes: set[str] = set()
    for index, cycle in enumerate(cycles):
        case_count += len(cycle["cases"])
        shapes.update(
            case["task_shape"]
            for case in cycle["cases"]
            if isinstance(case.get("task_shape"), str)
        )
        if index + 1 >= 10 and case_count >= 20 and len(shapes) >= 2:
            return index
    return None


def build_cohort_status(cycles: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = _validate_and_sort_cycles(cycles)
    cutoff = _cohort_cutoff(ordered)

    if cutoff is None:
        observed_cases = [case for cycle in ordered for case in cycle["cases"]]
        return {
            "schema_version": 1,
            "status": "COLLECTING",
            "cohort_frozen": False,
            "active_hour_cycles_observed": len(ordered),
            "candidate_events_observed": len(observed_cases),
            "task_shapes_observed": sorted({case["task_shape"] for case in observed_cases}),
            "minimum_raw_collection_met": False,
            "cutoff_active_hour_id": None,
            "cohort_case_ids": [],
            "resolved_survivors": 0,
            "resolved_decisive_negatives": 0,
            "unresolved_cases": 0,
            "replacement_benchmark_ready": False,
            "economic_conclusion": "NO_PROVEN_EDGE",
        }

    cohort_cycles = ordered[: cutoff + 1]
    cohort_cases: list[tuple[int, dict[str, Any]]] = []
    for cycle_index, cycle in enumerate(cohort_cycles):
        for case in cycle["cases"]:
            cohort_cases.append((cycle_index, case))

    resolution_rows: list[dict[str, Any]] = []
    survivor_count = 0
    negative_count = 0
    unresolved_count = 0
    for cycle_index, case in cohort_cases:
        resolution = resolve_case(case, ordered[cycle_index + 1 :])
        resolution_rows.append(resolution)
        if resolution["ground_truth_class"] == "SURVIVOR":
            survivor_count += 1
        elif resolution["ground_truth_class"] == "DECISIVE_NEGATIVE":
            negative_count += 1
        else:
            unresolved_count += 1

    case_ids = [case["case_id"] for _, case in cohort_cases]
    cutoff_hour = cohort_cycles[-1]["active_hour_id"]
    lock_core = {
        "cutoff_active_hour_id": cutoff_hour,
        "cohort_case_ids": case_ids,
        "cohort_cycle_ids": [cycle["active_hour_id"] for cycle in cohort_cycles],
    }
    cohort_hash = _sha256(lock_core)

    if unresolved_count:
        status = "RESOLVING"
    elif survivor_count < 1 or negative_count < 1:
        status = "INSUFFICIENT_CLASS_BALANCE"
    else:
        status = "READY_FOR_PAIRED_OBSERVATIONS"

    return {
        "schema_version": 1,
        "status": status,
        "cohort_frozen": True,
        "minimum_raw_collection_met": True,
        "cutoff_active_hour_id": cutoff_hour,
        "cohort_hash": cohort_hash,
        "cohort_cycle_ids": lock_core["cohort_cycle_ids"],
        "cohort_case_ids": case_ids,
        "cohort_case_count": len(case_ids),
        "cohort_cycle_count": len(cohort_cycles),
        "task_shapes_observed": sorted({case["task_shape"] for _, case in cohort_cases}),
        "resolution_cycles_available": len(ordered) - len(cohort_cycles),
        "resolved_survivors": survivor_count,
        "resolved_decisive_negatives": negative_count,
        "unresolved_cases": unresolved_count,
        "resolutions": resolution_rows,
        "replacement_benchmark_ready": status == "READY_FOR_PAIRED_OBSERVATIONS",
        "economic_conclusion": "NO_PROVEN_EDGE",
    }


def write_cohort_lock(output_dir: Path, status: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(status, dict) or status.get("cohort_frozen") is not True:
        raise ValueError("cohort_not_frozen")
    lock = {
        "schema_version": 1,
        "cutoff_active_hour_id": status["cutoff_active_hour_id"],
        "cohort_hash": status["cohort_hash"],
        "cohort_cycle_ids": status["cohort_cycle_ids"],
        "cohort_case_ids": status["cohort_case_ids"],
    }
    path = Path(output_dir) / "cohort_lock.json"
    encoded = json.dumps(lock, indent=2, sort_keys=True) + "\n"
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing == encoded:
            return {"status": "IDEMPOTENT", "path": str(path), "cohort_hash": lock["cohort_hash"]}
        raise ValueError("cohort_lock_conflict")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(encoded, encoding="utf-8")
    tmp.replace(path)
    return {"status": "CREATED", "path": str(path), "cohort_hash": lock["cohort_hash"]}
