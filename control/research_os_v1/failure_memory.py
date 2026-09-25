from __future__ import annotations

from copy import deepcopy
from typing import Any

from .policy import load_failure_patterns


class UnknownFailurePattern(KeyError):
    pass


REQUIRED_PATTERN_FIELDS = {
    "id", "name", "gate", "trigger", "required_check", "default_effect",
}


def _required_text(item: dict[str, Any], key: str, index: int) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"failure_pattern_field_required:{index}:{key}")
    return value.strip()


def pattern_index(obj: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    source = deepcopy(obj if obj is not None else load_failure_patterns())
    if not isinstance(source, dict):
        raise ValueError("failure_memory_must_be_object")
    if source.get("schema_version") != 1 or isinstance(source.get("schema_version"), bool):
        raise ValueError("unsupported_failure_memory_schema_version")
    patterns = source.get("patterns")
    if not isinstance(patterns, list) or not patterns:
        raise ValueError("failure_patterns_must_be_nonempty_list")

    out: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(patterns):
        if not isinstance(item, dict):
            raise ValueError(f"failure_pattern_must_be_object:{index}")
        missing = sorted(REQUIRED_PATTERN_FIELDS - set(item))
        if missing:
            raise ValueError(
                f"failure_pattern_fields_missing:{index}:{','.join(missing)}"
            )
        normalized = deepcopy(item)
        for key in REQUIRED_PATTERN_FIELDS:
            normalized[key] = _required_text(item, key, index)
        pid = normalized["id"]
        if pid in out:
            raise ValueError(f"duplicate_failure_pattern:{pid}")
        out[pid] = normalized
    return out


def required_checks(pattern_ids: list[str], obj: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Translate explicit pattern hits into mandatory checks.

    Pattern detection itself is done by a worker or deterministic detector.
    This function never auto-kills a candidate; it only returns required checks.
    """
    if not isinstance(pattern_ids, list):
        raise ValueError("failure_pattern_ids_must_be_list")
    clean_ids: list[str] = []
    for index, value in enumerate(pattern_ids):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"failure_pattern_id_invalid:{index}")
        clean_ids.append(value.strip())

    idx = pattern_index(obj)
    checks = []
    for pid in sorted(set(clean_ids)):
        if pid not in idx:
            raise UnknownFailurePattern(pid)
        item = idx[pid]
        checks.append({
            "failure_pattern_id": pid,
            "name": item["name"],
            "gate": item["gate"],
            "required_check": item["required_check"],
            "default_effect": item["default_effect"],
            "automatic_kill": False,
        })
    return checks
