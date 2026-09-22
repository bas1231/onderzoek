from __future__ import annotations

import argparse
import json
from pathlib import Path

from .prospective_cohort import build_cohort_status, load_cycle_directory
from .prospective_metrics import build_observation_set
from .prospective_pairing import build_paired_benchmark


def _load_object(path: Path) -> dict:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid_json:{path}:{type(exc).__name__}") from exc
    if not isinstance(obj, dict):
        raise ValueError(f"json_object_required:{path}")
    return obj


def _write_once(path: Path, payload: dict) -> None:
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing != encoded:
            raise ValueError(f"output_conflict:{path}")
        return
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(encoded, encoding="utf-8")
    tmp.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate the full Research OS V1 prospective shadow benchmark from "
            "immutable cycle captures and structured baseline/challenger telemetry."
        )
    )
    parser.add_argument("--collection-dir", required=True, type=Path)
    parser.add_argument("--baseline-telemetry", required=True, type=Path)
    parser.add_argument("--challenger-telemetry", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    cycles = load_cycle_directory(args.collection_dir)
    cohort = build_cohort_status(cycles)
    baseline_telemetry = _load_object(args.baseline_telemetry)
    challenger_telemetry = _load_object(args.challenger_telemetry)

    baseline = build_observation_set(cohort, baseline_telemetry, "BASELINE")
    challenger = build_observation_set(cohort, challenger_telemetry, "CHALLENGER")
    result = build_paired_benchmark(cohort, baseline, challenger)

    output = {
        "schema_version": 1,
        "cohort_status": cohort,
        "baseline_observations": baseline,
        "challenger_observations": challenger,
        "benchmark": result,
    }
    if args.output_dir is not None:
        _write_once(args.output_dir / "baseline_observations.json", baseline)
        _write_once(args.output_dir / "challenger_observations.json", challenger)
        _write_once(args.output_dir / "benchmark_result.json", result)
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
