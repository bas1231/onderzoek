from __future__ import annotations

from typing import Any

from .policy import load_failure_patterns


class UnknownFailurePattern(KeyError):
    pass


def pattern_index(obj: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    obj = obj or load_failure_patterns()
    patterns = obj.get("patterns") or []
    out: dict[str, dict[str, Any]] = {}
    for item in patterns:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        pid = str(item["id"])
        if pid in out:
            raise ValueError(f"duplicate_failure_pattern:{pid}")
        out[pid] = item
    return out


def required_checks(pattern_ids: list[str], obj: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Translate explicit pattern hits into mandatory checks.

    Pattern detection itself is done by a worker or deterministic detector.
    This function never auto-kills a candidate; it only returns required checks.
    """
    idx = pattern_index(obj)
    checks = []
    for pid in sorted(set(map(str, pattern_ids))):
        if pid not in idx:
            raise UnknownFailurePattern(pid)
        item = idx[pid]
        checks.append({
            "failure_pattern_id": pid,
            "name": item.get("name"),
            "gate": item.get("gate"),
            "required_check": item.get("required_check"),
            "default_effect": item.get("default_effect"),
            "automatic_kill": False,
        })
    return checks
