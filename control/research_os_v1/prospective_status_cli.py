from __future__ import annotations

import argparse
import json
from pathlib import Path

from .prospective_cohort import build_cohort_status, load_cycle_directory, write_cohort_lock


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report deterministic prospective Research OS cohort status."
    )
    parser.add_argument("--collection-dir", required=True, type=Path)
    parser.add_argument(
        "--write-lock",
        action="store_true",
        help="Write immutable cohort_lock.json once the automatic cutoff is reached.",
    )
    args = parser.parse_args()

    cycles = load_cycle_directory(args.collection_dir)
    status = build_cohort_status(cycles)
    if args.write_lock and status.get("cohort_frozen") is True:
        status = dict(status)
        status["cohort_lock_write"] = write_cohort_lock(args.collection_dir, status)
    elif args.write_lock:
        status = dict(status)
        status["cohort_lock_write"] = {"status": "NOT_READY", "reason": "cohort_not_frozen"}

    print(json.dumps(status, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
