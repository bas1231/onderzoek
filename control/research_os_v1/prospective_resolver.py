from __future__ import annotations

from typing import Any

from .prospective_collector import validate_cycle_capture


RESOLUTION_POLICY_VERSION = 1
ACTIVE_OR_WAITING = {
    "QUEUED",
    "NEEDS_DIRECTOR",
    "EXPERIMENT_REQUIRED",
    "RUNNING",
    "WAITING_FOR_DATA",
    "WAITING_FOR_RESULT",
    "RESULT_READY",
    "NEEDS_REVISION",
    "PARKED",
    "PROMOTION_CANDIDATE",
}


def _required_text(value: Any, error: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(error)
    return value.strip()


def _basis_ref(cycle: dict[str, Any], case: dict[str, Any]) -> str:
    return f"cycle:{cycle['active_hour_id']}#case:{case['case_id']}"


def _candidate_case(cycle: dict[str, Any], candidate_id: str) -> dict[str, Any] | None:
    matches = [
        case
        for case in cycle.get("cases", [])
        if isinstance(case, dict) and case.get("candidate_id") == candidate_id
    ]
    if len(matches) > 1:
        raise ValueError(f"duplicate_candidate_event_in_cycle:{candidate_id}")
    return matches[0] if matches else None


def _negative_reason(candidate_capture: dict[str, Any]) -> str | None:
    if candidate_capture.get("queue_status") == "CLOSED_NEGATIVE":
        return "queue_status_closed_negative"
    if candidate_capture.get("economic_status") == "TESTED_NEGATIVE":
        return "economic_status_tested_negative"
    gates = candidate_capture.get("required_gates")
    if gates is not None and not isinstance(gates, dict):
        raise ValueError("required_gates_must_be_object")
    for gate, state in sorted((gates or {}).items()):
        if state == "FAIL":
            return f"required_gate_fail:{gate}"
    return None


def _progress_signal(candidate_capture: dict[str, Any]) -> bool:
    gates = candidate_capture.get("required_gates")
    if gates is not None and not isinstance(gates, dict):
        raise ValueError("required_gates_must_be_object")
    if any(state == "PASS" for state in (gates or {}).values()):
        return True
    question = candidate_capture.get("next_decisive_question")
    if isinstance(question, str) and question.strip():
        return True
    for key in ("blockers", "dependencies"):
        value = candidate_capture.get(key)
        if value is not None and not isinstance(value, list):
            raise ValueError(f"{key}_must_be_list")
        if value:
            return True
    return candidate_capture.get("queue_status") in {"WAITING_FOR_DATA", "WAITING_FOR_RESULT"}


def resolve_case(
    captured_case: dict[str, Any],
    later_cycles: list[dict[str, Any]],
) -> dict[str, Any]:
    """Resolve ground truth without mutating the immutable capture.

    later_cycles must be supplied in accepted chronological collection order.
    Only later cycles that contain the same candidate as a qualifying case count
    toward the three-observation survivor horizon. Any decisive negative takes
    precedence immediately. Missing observations remain unresolved rather than
    being imputed.
    """
    if not isinstance(captured_case, dict):
        raise ValueError("captured_case_must_be_object")
    candidate_id = _required_text(captured_case.get("candidate_id"), "candidate_id_required")
    case_id = _required_text(captured_case.get("case_id"), "case_id_required")
    capture_hour = _required_text(captured_case.get("active_hour_id"), "active_hour_id_required")
    if not isinstance(later_cycles, list):
        raise ValueError("later_cycles_must_be_list")

    seen_hours: set[str] = set()
    observations: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for cycle in later_cycles:
        errors = validate_cycle_capture(cycle)
        if errors:
            raise ValueError("invalid_later_cycle:" + ",".join(errors))
        hour = _required_text(cycle.get("active_hour_id"), "later_active_hour_id_required")
        if hour == capture_hour:
            raise ValueError("later_cycle_reuses_capture_hour")
        if hour in seen_hours:
            raise ValueError(f"duplicate_later_active_hour:{hour}")
        seen_hours.add(hour)
        match = _candidate_case(cycle, candidate_id)
        if match is not None:
            observations.append((cycle, match))

    for cycle, case in observations:
        candidate_capture = case.get("candidate_capture")
        if not isinstance(candidate_capture, dict):
            raise ValueError("candidate_capture_required")
        reason = _negative_reason(candidate_capture)
        if reason is not None:
            return {
                "schema_version": 1,
                "resolution_policy_version": RESOLUTION_POLICY_VERSION,
                "case_id": case_id,
                "candidate_id": candidate_id,
                "status": "RESOLVED",
                "ground_truth_class": "DECISIVE_NEGATIVE",
                "reason": reason,
                "basis_refs": [_basis_ref(cycle, case)],
                "later_candidate_observations": len(observations),
            }

    if len(observations) >= 3:
        cycle, case = observations[-1]
        candidate_capture = case.get("candidate_capture")
        if not isinstance(candidate_capture, dict):
            raise ValueError("candidate_capture_required")
        queue_status = candidate_capture.get("queue_status")
        if queue_status in ACTIVE_OR_WAITING and _progress_signal(candidate_capture):
            return {
                "schema_version": 1,
                "resolution_policy_version": RESOLUTION_POLICY_VERSION,
                "case_id": case_id,
                "candidate_id": candidate_id,
                "status": "RESOLVED",
                "ground_truth_class": "SURVIVOR",
                "reason": "three_later_observations_active_with_progress_signal",
                "basis_refs": [_basis_ref(cycle, case)],
                "later_candidate_observations": len(observations),
            }

    return {
        "schema_version": 1,
        "resolution_policy_version": RESOLUTION_POLICY_VERSION,
        "case_id": case_id,
        "candidate_id": candidate_id,
        "status": "UNRESOLVED",
        "ground_truth_class": None,
        "reason": "insufficient_decisive_evidence_or_survivor_horizon",
        "basis_refs": [],
        "later_candidate_observations": len(observations),
    }
