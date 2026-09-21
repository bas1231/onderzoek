#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,159}$")
DEFAULT_ROOT = Path.cwd()


def read_json(path: Path):
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def tail_text(path: Path, limit: int) -> str:
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[-limit:]


def inspect_task(root: Path, task_id: str) -> dict:
    if not SAFE_ID.fullmatch(task_id):
        raise ValueError("INVALID_TASK_ID")

    root = root.resolve()
    result_dir = (root / "control" / "results" / task_id).resolve()
    expected_parent = (root / "control" / "results").resolve()
    if result_dir.parent != expected_parent:
        raise ValueError("UNSAFE_RESULT_PATH")

    result_path = result_dir / "RESULT.json"
    if not result_path.is_file():
        raise FileNotFoundError(f"RESULT_NOT_FOUND:{task_id}")

    result = read_json(result_path)
    if result.get("task_id") != task_id:
        raise ValueError("RESULT_TASK_ID_MISMATCH")

    lifecycle_path = root / "control" / "lifecycle" / f"{task_id}.json"
    lifecycle = read_json(lifecycle_path) if lifecycle_path.is_file() else None

    task_locations = {}
    for state in ("pending", "running", "completed", "failed"):
        path = root / "control" / "tasks" / state / f"{task_id}.json"
        if path.is_file():
            task_locations[state] = read_json(path)

    return {
        "task_id": task_id,
        "result": result,
        "stdout": tail_text(result_dir / "stdout.log", 30000),
        "stderr": tail_text(result_dir / "stderr.log", 15000),
        "lifecycle": lifecycle,
        "task_locations": task_locations,
        "result_path": str(result_path),
        "economic_conclusion": "NO_PROVEN_EDGE",
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"status": "BLOCKED", "reason": "USAGE: TASK_ID"}))
        return 2

    task_id = sys.argv[1]
    try:
        payload = inspect_task(DEFAULT_ROOT, task_id)
    except Exception as exc:
        print(json.dumps({
            "status": "BLOCKED",
            "task_id": task_id,
            "reason": f"{type(exc).__name__}: {exc}",
            "economic_conclusion": "NO_PROVEN_EDGE",
            "live_trading": False,
            "paid_action": False,
            "wallet_action": False,
        }, indent=2, sort_keys=True))
        return 2

    payload["status"] = "PASS"
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
