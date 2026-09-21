from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .legacy_adapter import packets_to_tasks
from .shadow_cycle import build_shadow_plan


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid_json:{path}:{type(exc).__name__}:{exc}") from exc


def _require_dir(path: Path, label: str) -> None:
    if not path.exists():
        raise ValueError(f"{label}_directory_missing:{path}")
    if not path.is_dir():
        raise ValueError(f"{label}_path_not_directory:{path}")


def load_candidates(candidate_dir: Path) -> list[dict[str, Any]]:
    _require_dir(candidate_dir, "candidate")
    rows: list[dict[str, Any]] = []
    seen: dict[str, Path] = {}
    for path in sorted(candidate_dir.glob("*.json")):
        if path.name.startswith("_"):
            continue
        obj = load_json(path)
        if not isinstance(obj, dict):
            raise ValueError(f"candidate_not_object:{path}")
        candidate_id = str(obj.get("candidate_id") or "").strip()
        if not candidate_id:
            raise ValueError(f"candidate_id_missing:{path}")
        if candidate_id in seen:
            raise ValueError(
                f"duplicate_candidate_id:{candidate_id}:{seen[candidate_id]}:{path}"
            )
        seen[candidate_id] = path
        rows.append(obj)
    return rows


def load_packets(packet_dir: Path) -> list[dict[str, Any]]:
    _require_dir(packet_dir, "packet")
    rows: list[dict[str, Any]] = []
    seen: dict[str, Path] = {}
    for path in sorted(packet_dir.glob("*.json")):
        if path.name.startswith("_"):
            continue
        obj = load_json(path)
        if not isinstance(obj, dict):
            raise ValueError(f"packet_not_object:{path}")
        agent_id = str(obj.get("agent_id") or "").strip()
        if not agent_id:
            raise ValueError(f"packet_agent_id_missing:{path}")
        if agent_id in seen:
            raise ValueError(
                f"duplicate_packet_agent_id:{agent_id}:{seen[agent_id]}:{path}"
            )
        seen[agent_id] = path
        rows.append(obj)
    return rows


def build_from_paths(candidate_dir: Path, packet_dir: Path, source_commit: str) -> dict[str, Any]:
    if not str(source_commit or "").strip():
        raise ValueError("source_commit_required")
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
