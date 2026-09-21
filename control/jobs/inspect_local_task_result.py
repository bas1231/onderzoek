#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SAFE_ID = re.compile(r"^[A-Za-z0-9._-]{3,160}$")
ROOT = Path.cwd()


def read_json(path: Path):
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value
    except Exception as exc:
        return {"_error": f"{type(exc).__name__}: {exc}", "_path": str(path)}


def main() -> int:
    if len(sys.argv) != 2 or not SAFE_ID.fullmatch(sys.argv[1]):
        print(json.dumps({"status": "BLOCKED", "reason": "INVALID_TASK_ID"}))
        return 2

    task_id = sys.argv[1]
    candidates = {
        "result": ROOT / "control" / "results" / task_id / "RESULT.json",
        "lifecycle": ROOT / "control" / "lifecycle" / f"{task_id}.json",
    }
    task_locations = {}
    for state in ("pending", "running", "completed", "failed"):
        path = ROOT / "control" / "tasks" / state / f"{task_id}.json"
        if path.is_file():
            task_locations[state] = read_json(path)

    payload = {
        "task_id": task_id,
        "result": read_json(candidates["result"]),
        "lifecycle": read_json(candidates["lifecycle"]),
        "task_locations": task_locations,
        "economic_conclusion": "NO_PROVEN_EDGE",
        "live_trading": False,
        "paid_action": False,
        "wallet_action": False,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
