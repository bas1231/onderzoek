from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .prospective_collector import build_cycle_capture, write_cycle_capture


def _load_json_objects(directory: Path) -> list[dict[str, Any]]:
    if not directory.exists() or not directory.is_dir():
        raise ValueError(f"directory_missing:{directory}")
    rows: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ValueError(f"invalid_json:{path}:{type(exc).__name__}") from exc
        if not isinstance(obj, dict):
            raise ValueError(f"json_object_required:{path}")
        rows.append(obj)
    if not rows:
        raise ValueError(f"no_json_objects:{directory}")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture one prospective Research OS shadow cycle without mutating active runtime."
    )
    parser.add_argument("--candidates", required=True, type=Path)
    parser.add_argument("--packets", required=True, type=Path)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--active-hour-id")
    args = parser.parse_args()

    active_hour_id = args.active_hour_id or args.packets.name
    candidates = _load_json_objects(args.candidates)
    packets = _load_json_objects(args.packets)
    cycle = build_cycle_capture(
        active_hour_id=active_hour_id,
        source_commit=args.source_commit,
        candidates=candidates,
        packets=packets,
    )
    write_result = write_cycle_capture(args.output_dir, cycle)
    summary = {
        "status": write_result["status"],
        "mode": cycle["mode"],
        "active_hour_id": cycle["active_hour_id"],
        "case_count": cycle["case_count"],
        "case_ids": [case["case_id"] for case in cycle["cases"]],
        "capture_hash": cycle["capture_hash"],
        "path": write_result["path"],
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "runtime_mutation": False,
        "economic_conclusion": "NO_PROVEN_EDGE",
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
