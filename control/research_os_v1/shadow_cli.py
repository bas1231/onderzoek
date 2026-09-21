from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .legacy_adapter import packets_to_tasks
from .shadow_cycle import build_shadow_plan


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_candidates(candidate_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(candidate_dir.glob("*.json")):
        obj = load_json(path)
        if isinstance(obj, dict) and obj.get("candidate_id"):
            rows.append(obj)
    return rows


def load_packets(packet_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(packet_dir.glob("*.json")):
        if path.name.startswith("_"):
            continue
        obj = load_json(path)
        if isinstance(obj, dict) and obj.get("agent_id"):
            rows.append(obj)
    return rows


def build_from_paths(candidate_dir: Path, packet_dir: Path, source_commit: str) -> dict[str, Any]:
    candidates = load_candidates(candidate_dir)
    packets = load_packets(packet_dir)
    tasks = packets_to_tasks(packets, run_id=packet_dir.name)
    result = build_shadow_plan(candidates, tasks, source_commit=source_commit)
    result["input_summary"] = {
        "candidate_count": len(candidates),
        "packet_count": len(packets),
        "task_count": len(tasks),
        "packet_run_id": packet_dir.name,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Research OS V1 read-only shadow planner")
    parser.add_argument("--candidates", type=Path, default=Path("knowledge/candidates"))
    parser.add_argument("--packets", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    result = build_from_paths(args.candidates, args.packets, args.source_commit)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
