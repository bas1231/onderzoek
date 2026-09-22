from __future__ import annotations

import argparse
import json
from pathlib import Path

from .prospective_cohort import build_cohort_status, load_cycle_directory
from .prospective_materialize import materialize_observation_inputs
from .prospective_metrics import build_observation_set
from .prospective_pairing import build_paired_benchmark


def _write_once(path: Path, payload: dict) -> None:
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != encoded:
            raise ValueError(f"output_conflict:{path}")
        return
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(encoded, encoding="utf-8")
    tmp.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Recompute the full frozen Research OS V1 prospective benchmark "
            "directly from immutable cycle captures and per-cycle raw telemetry."
        )
    )
    parser.add_argument("--collection-dir", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    cycles = load_cycle_directory(args.collection_dir)
    cohort = build_cohort_status(cycles)
    if cohort.get("replacement_benchmark_ready") is not True:
        print(json.dumps({
            "schema_version": 1,
            "status": cohort.get("status"),
            "cohort_status": cohort,
            "benchmark_evaluated": False,
            "economic_conclusion": "NO_PROVEN_EDGE",
        }, indent=2, sort_keys=True))
        return 0

    baseline_raw, challenger_raw = materialize_observation_inputs(
        args.collection_dir, cohort
    )
    baseline = build_observation_set(cohort, baseline_raw, "BASELINE")
    challenger = build_observation_set(cohort, challenger_raw, "CHALLENGER")
    benchmark = build_paired_benchmark(cohort, baseline, challenger)

    output = {
        "schema_version": 1,
        "status": benchmark["status"],
        "cohort_status": cohort,
        "benchmark_evaluated": True,
        "benchmark": benchmark,
        "economic_conclusion": "NO_PROVEN_EDGE",
        "automatic_runtime_replacement_authorized": False,
    }
    if args.output_dir is not None:
        _write_once(args.output_dir / "baseline_observations.json", baseline)
        _write_once(args.output_dir / "challenger_observations.json", challenger)
        _write_once(args.output_dir / "benchmark_result.json", benchmark)
        _write_once(args.output_dir / "benchmark_full_status.json", output)
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
