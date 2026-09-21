from __future__ import annotations

from copy import deepcopy
from typing import Any


def evaluate(
    candidate: dict[str, Any],
    changed_conditions: list[str],
    observed_at: str,
) -> dict[str, Any]:
    """Reopen a killed candidate only when an explicit stored condition changed.

    Prior validation is not inherited as proof in the new regime.
    """
    out = deepcopy(candidate)
    killed = str(out.get("economic_status") or "").upper() == "TESTED_NEGATIVE" or str(out.get("queue_status") or "").upper() == "CLOSED_NEGATIVE"
    conditions = set(map(str, out.get("resurrection_conditions") or []))
    changed = sorted(conditions & set(map(str, changed_conditions)))

    if not killed or not changed:
        return {
            "resurrected": False,
            "candidate": out,
            "matched_conditions": changed,
            "reason": "no_stored_resurrection_condition_changed" if killed else "candidate_not_killed",
        }

    out["queue_status"] = "NEEDS_REVISION"
    out["economic_status"] = "NO_PROVEN_EDGE"
    out["phase"] = "DISCOVERED"
    out["updated_at"] = observed_at
    out["blockers"] = sorted(set(list(out.get("blockers") or []) + ["RESURRECTED_REQUIRES_FRESH_VALIDATION"]))
    gates = dict(out.get("required_gates") or {})
    for gate in list(gates):
        if gate not in {"source_provenance"}:
            gates[gate] = "PENDING"
    out["required_gates"] = gates

    return {
        "resurrected": True,
        "candidate": out,
        "matched_conditions": changed,
        "reason": "EDGE_RESURRECTION_CONDITION_CHANGED",
        "old_validation_inherited": False,
    }
