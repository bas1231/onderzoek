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
    "independent_reproduction",
    "shadow",
]


def evaluate(candidate: dict[str, Any], signal_required: bool = True) -> dict[str, Any]:
    """Evaluate promotion eligibility without allowing Director overrides.

    `signal_required=False` is not permission to silently skip a signal gate. The
    candidate must explicitly record `signal_edge=NOT_APPLICABLE`; otherwise the
    route fails closed. This only returns scientific state and never authorizes
    live trading.
    """
    gates = (
        candidate.get("required_gates")
        if isinstance(candidate.get("required_gates"), dict)
        else {}
    )
    required = list(BASE_REQUIRED)

    if signal_required:
        required.insert(3, "signal_edge")
    else:
        signal_state = str(gates.get("signal_edge") or "UNKNOWN").upper()
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

    failed: list[str] = []
    pending: list[str] = []
    for gate in required:
        state = str(gates.get(gate) or "UNKNOWN").upper()
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
