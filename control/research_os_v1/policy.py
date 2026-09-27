from __future__ import annotations

import json
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent


class PolicyError(RuntimeError):
    pass


def load_json(name: str) -> dict[str, Any]:
    path = BASE / name
    if not path.is_file():
        raise PolicyError(f"missing_policy:{name}")
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise PolicyError(f"invalid_policy:{name}:{exc}") from exc
    if not isinstance(obj, dict):
        raise PolicyError(f"policy_not_object:{name}")
    return obj


def load_governor_policy() -> dict[str, Any]:
    return load_json("governor_policy.json")


def load_scheduler_policy() -> dict[str, Any]:
    return load_json("scheduler_policy.json")


def load_task_shape_policy() -> dict[str, Any]:
    return load_json("task_shape_policy.json")


def load_failure_patterns() -> dict[str, Any]:
    return load_json("failure_patterns.json")
