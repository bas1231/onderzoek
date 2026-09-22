from __future__ import annotations

from typing import Any

BASE_REQUIRED = [
    "source_provenance",
    "point_in_time",
    "mechanism",
    "market_edge",
    "execution_reality",
    "prebuild_killer",
    "chief_falsifier",
    "validation",
    "holdout",
    "independent_reproduction",
    "shadow",
]
ALLOWED_GATE_STATES = {"PASS", "FAIL", "PENDING", "UNKNOWN", "NOT_APPLICABLE"}


def _gate_map(candidate: dict[str, Any]) -> dict[str, str]:
    value = candidate.get("required_gates")
    if not isinstance(value, dict):
        return {}

    out: dict[str, str] = {}
    for raw_name, raw_state in value.items():
        if not isinstance(raw_name, str) or not raw_name.strip():
            raise ValueError("gate_name_must_be_nonempty_string")
        if not isinstance(raw_state, str):
            raise ValueError(f"gate_state_must_be_string:{raw_name}")
        name = raw_name.strip()
        state = raw_state.strip().upper()
        if state not in ALLOWED_GATE_STATES:
            raise ValueError(f"invalid_gate_state:{name}:{state}")
        out[name] = state
    return out


def evaluate(candidate: dict[str, Any], signal_required: bool = True) -> dict[str, Any]:
    """Evaluate scientific promotion eligibility with fail-closed future gates.

    Every gate present in ``required_gates`` is treated as required. This is
    deliberate future-proofing: adding a new required gate elsewhere may never
    make promotion *easier* merely because this evaluator does not know its
    name yet. Unknown/new gates therefore need an explicit PASS until dedicated
    semantics are added here.

    ``signal_required=False`` is not permission to silently skip the signal
    gate: it must explicitly be ``NOT_APPLICABLE``. Holdout is always required.
    This function never authorizes live trading.
    """
    if not isinstance(candidate, dict):
        raise ValueError("candidate_must_be_object")
    if not isinstance(signal_required, bool):
        raise ValueError("signal_required_must_be_boolean")

    gates = _gate_map(candidate)
    required = list(BASE_REQUIRED)

    if signal_required:
        required.insert(3, "signal_edge")
    else:
        signal_state = gates.get("signal_edge", "UNKNOWN")
        if signal_state != "NOT_APPLICABLE":
            return {
                "eligible": False,
                "status": "BLOCKED_GATE",
                "failed_gates": ["signal_edge"],
                "pending_gates": [],
                "block_reasons": ["signal_edge_not_explicitly_not_applicable"],
                "director_override_allowed": False,
                "live_trading_authorized": False,
                "economic_conclusion": "NO_PROVEN_EDGE",
            }

    # Future/extension gates are also binding. A newly introduced requirement
    # cannot be ignored by an older promotion evaluator.
    extension_gates = sorted(
        gate for gate in gates if gate not in set(required) | {"signal_edge"}
    )
    required.extend(extension_gates)

    failed: list[str] = []
    pending: list[str] = []
    for gate in required:
        state = gates.get(gate, "UNKNOWN")
        if state == "FAIL":
            failed.append(gate)
        elif state != "PASS":
            pending.append(gate)

    if failed:
        status = "BLOCKED_GATE"
    elif pending:
        status = "INCOMPLETE_GATES"
    else:
        status = "PROMOTION_CANDIDATE"

    return {
        "eligible": not failed and not pending,
        "status": status,
        "failed_gates": failed,
        "pending_gates": pending,
        "block_reasons": [],
        "director_override_allowed": False,
        "live_trading_authorized": False,
        "economic_conclusion": (
            "PROVEN_EDGE_CANDIDATE"
            if status == "PROMOTION_CANDIDATE"
            else "NO_PROVEN_EDGE"
        ),
    }
