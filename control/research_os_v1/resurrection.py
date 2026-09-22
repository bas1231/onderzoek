from __future__ import annotations

from copy import deepcopy
from typing import Any


def _required_text(value: Any, error: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(error)
    return value.strip()


def _string_list(value: Any, error: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(error)
    out: list[str] = []
    for item in value:
        out.append(_required_text(item, error))
    return out


def _gate_map(value: Any, error: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(error)
    out: dict[str, Any] = {}
    for raw_gate, state in value.items():
        gate = _required_text(raw_gate, "gate_name_must_be_nonempty_string")
        out[gate] = deepcopy(state)
    return out


def _stored_resurrection_conditions(candidate: dict[str, Any]) -> list[str]:
    if candidate.get("resurrection_conditions") is not None:
        return _string_list(
            candidate.get("resurrection_conditions"),
            "resurrection_conditions_must_be_list_of_nonempty_strings",
        )
    legacy = candidate.get("resume_condition")
    if legacy is None:
        return []
    return [_required_text(legacy, "resume_condition_must_be_nonempty_string")]


def evaluate(
    candidate: dict[str, Any],
    changed_conditions: list[str],
    observed_at: str,
) -> dict[str, Any]:
    """Reopen a killed candidate only when an explicit stored condition changed.

    Resurrection starts a fresh evidentiary regime. Both canonical
    ``required_gates`` and legacy ``gates`` are reset as one union so an old PASS
    can never leak back through the compatibility representation. Prior values
    remain only in ``resurrection_history``.
    """
    if not isinstance(candidate, dict):
        raise ValueError("candidate_must_be_object")
    changed_list = _string_list(
        changed_conditions,
        "changed_conditions_must_be_list_of_nonempty_strings",
    )
    observed = _required_text(observed_at, "observed_at_required")

    out = deepcopy(candidate)
    killed = (
        str(out.get("economic_status") or "").upper() == "TESTED_NEGATIVE"
        or str(out.get("queue_status") or "").upper() == "CLOSED_NEGATIVE"
    )

    stored_conditions = _stored_resurrection_conditions(out)
    conditions = set(stored_conditions)
    changed = sorted(conditions & set(changed_list))

    if not killed or not changed:
        return {
            "resurrected": False,
            "candidate": out,
            "matched_conditions": changed,
            "reason": (
                "no_stored_resurrection_condition_changed"
                if killed
                else "candidate_not_killed"
            ),
        }

    canonical_gates = _gate_map(
        out.get("required_gates"),
        "required_gates_must_be_object",
    )
    legacy_gates = _gate_map(
        out.get("gates"),
        "gates_must_be_object",
    )
    all_gate_names = sorted(set(canonical_gates) | set(legacy_gates))
    reset_gates = {gate: "PENDING" for gate in all_gate_names}

    blockers = _string_list(
        out.get("blockers"),
        "blockers_must_be_list_of_nonempty_strings",
    )

    history_value = out.get("resurrection_history")
    if history_value is None:
        history: list[dict[str, Any]] = []
    elif not isinstance(history_value, list) or not all(
        isinstance(item, dict) for item in history_value
    ):
        raise ValueError("resurrection_history_must_be_list_of_objects")
    else:
        history = deepcopy(history_value)

    previous = {
        "observed_at": observed,
        "matched_conditions": changed,
        "phase": out.get("phase"),
        "queue_status": out.get("queue_status"),
        "economic_status": out.get("economic_status"),
        "required_gates": deepcopy(canonical_gates),
        "legacy_gates": deepcopy(legacy_gates),
    }
    history.append(previous)

    out["queue_status"] = "NEEDS_REVISION"
    out["economic_status"] = "NO_PROVEN_EDGE"
    out["phase"] = "DISCOVERED"
    out["updated_at"] = observed
    out["resurrection_history"] = history
    out["blockers"] = sorted(
        set(blockers + ["RESURRECTED_REQUIRES_FRESH_VALIDATION"])
    )
    out["required_gates"] = deepcopy(reset_gates)
    if "gates" in out:
        out["gates"] = deepcopy(reset_gates)
    out["resurrection_conditions"] = stored_conditions

    return {
        "resurrected": True,
        "candidate": out,
        "matched_conditions": changed,
        "reason": "EDGE_RESURRECTION_CONDITION_CHANGED",
        "old_validation_inherited": False,
        "old_gate_passes_inherited": False,
    }
