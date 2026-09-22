from __future__ import annotations

import argparse
import json
from pathlib import Path

from .prospective_cohort import build_cohort_status, load_cycle_directory
from .prospective_pairing import build_paired_benchmark


def _load_object(path: Path) -> dict:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid_json:{path}:{type(exc).__name__}") from exc
    if not isinstance(obj, dict):
        raise ValueError(f"json_object_required:{path}")
    return obj


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build the fail-closed paired Research OS prospective benchmark "
            "from the frozen cohort and exact baseline/challenger observation sets."
        )
    )
    parser.add_argument("--collection-dir", required=True, type=Path)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--challenger", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    cycles = load_cycle_directory(args.collection_dir)
    cohort_status = build_cohort_status(cycles)
    baseline = _load_object(args.baseline)
    challenger = _load_object(args.challenger)
    result = build_paired_benchmark(cohort_status, baseline, challenger)

    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if args.output.exists():
            existing = args.output.read_text(encoding="utf-8")
            if existing != encoded:
                raise ValueError(f"benchmark_output_conflict:{args.output}")
        else:
            tmp = args.output.with_suffix(args.output.suffix + ".tmp")
            tmp.write_text(encoded, encoding="utf-8")
            tmp.replace(args.output)
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
