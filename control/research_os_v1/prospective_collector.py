from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from .candidate_view import canonicalize
from .legacy_adapter import packets_to_tasks
from .scheduler import schedule


CAPTURE_SCHEMA_VERSION = 1
CASE_PREFIX = "ROS1"


def _required_text(value: Any, error: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(error)
    return value.strip()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def task_shape_label(task: dict[str, Any]) -> str:
    if not isinstance(task, dict):
        raise ValueError("task_must_be_object")
    shape = task.get("task_shape")
    if not isinstance(shape, dict):
        raise ValueError("task_shape_required")
    dep = shape.get("dependency_shape")
    par = shape.get("parallelism")
    if dep == "SEQUENTIAL" or par == "LOW":
        return "LOW_SEQUENTIAL"
    if dep == "INDEPENDENT" and par == "HIGH":
        return "HIGH_INDEPENDENT"
    return "MEDIUM_PARTIAL"


def _decision_map(scheduled: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if not isinstance(scheduled, dict):
        raise ValueError("scheduled_must_be_object")
    out: dict[str, dict[str, Any]] = {}
    selected = scheduled.get("selected")
    if not isinstance(selected, list):
        raise ValueError("scheduled_selected_must_be_list")
    for index, task_id in enumerate(selected):
        tid = _required_text(task_id, "selected_task_id_invalid")
        if tid in out:
            raise ValueError(f"duplicate_scheduled_task_id:{tid}")
        out[tid] = {
            "decision": "SELECTED",
            "reason": "scheduler_selected",
            "selected_order": index,
        }

    for bucket, default_decision in (("waiting", "WAITING"), ("blocked", "BLOCKED")):
        items = scheduled.get(bucket)
        if not isinstance(items, list):
            raise ValueError(f"scheduled_{bucket}_must_be_list")
        for item in items:
            if not isinstance(item, dict):
                raise ValueError(f"scheduled_{bucket}_item_must_be_object")
            tid = _required_text(item.get("task_id"), f"scheduled_{bucket}_task_id_invalid")
            if tid in out:
                raise ValueError(f"duplicate_scheduler_decision:{tid}")
            out[tid] = {
                "decision": str(item.get("decision") or default_decision),
                "reason": str(item.get("reason") or "unspecified"),
                "selected_order": None,
            }
    return out


def _packet_by_role(packets: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for packet in packets:
        if not isinstance(packet, dict):
            raise ValueError("packet_must_be_object")
        role = _required_text(packet.get("agent_id"), "packet_agent_id_required")
        if role in out:
            raise ValueError(f"duplicate_agent_packet:{role}")
        out[role] = deepcopy(packet)
    return out


def _representative_task(
    tasks: list[dict[str, Any]],
    decision_map: dict[str, dict[str, Any]],
    candidate_id: str,
) -> dict[str, Any] | None:
    linked = [task for task in tasks if task.get("candidate_id") == candidate_id]
    if not linked:
        return None

    def key(task: dict[str, Any]) -> tuple[Any, ...]:
        task_id = _required_text(task.get("task_id"), "task_id_required")
        decision = decision_map.get(task_id)
        selected_order = None if decision is None else decision.get("selected_order")
        is_selected = isinstance(selected_order, int) and not isinstance(selected_order, bool)
        state = task.get("state")
        return (
            0 if is_selected else 1,
            selected_order if is_selected else 10**9,
            0 if state == "READY" else 1,
            task_id,
        )

    return min(linked, key=key)


def _case_identity(
    active_hour_id: str,
    candidate_id: str,
    task: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": CAPTURE_SCHEMA_VERSION,
        "active_hour_id": active_hour_id,
        "candidate_id": candidate_id,
        "representative_task_id": _required_text(task.get("task_id"), "task_id_required"),
        "legacy_role": _required_text(task.get("legacy_role"), "legacy_role_required"),
        "task_shape": task_shape_label(task),
    }


def _case_id(identity: dict[str, Any]) -> str:
    return f"{CASE_PREFIX}-{_sha256(identity)[:24]}"


def _baseline_snapshot(packet: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    input_refs = packet.get("input_refs")
    routed = packet.get("routed_evidence")
    candidate_ids = packet.get("candidate_ids")
    return {
        "legacy_status": task.get("legacy_status"),
        "normalized_state": task.get("state"),
        "ai_result_present": isinstance(packet.get("ai_result"), dict),
        "input_ref_count": len(input_refs) if isinstance(input_refs, list) else 0,
        "routed_evidence_count": len(routed) if isinstance(routed, list) else 0,
        "candidate_id_count": len(candidate_ids) if isinstance(candidate_ids, list) else 0,
        "packet_hash": _sha256(packet),
    }


def build_cycle_capture(
    *,
    active_hour_id: str,
    source_commit: str,
    candidates: list[dict[str, Any]],
    packets: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build an immutable prospective capture for one ACTIVE-HOUR cycle.

    A benchmark case is one candidate observed in one ACTIVE-HOUR cycle and
    linked to at least one single-candidate legacy task. If several tasks point
    to the same candidate, exactly one representative task is chosen
    deterministically. No ground-truth label is assigned at capture time.
    """
    hour = _required_text(active_hour_id, "active_hour_id_required")
    commit = _required_text(source_commit, "source_commit_required")
    if not isinstance(candidates, list):
        raise ValueError("candidates_must_be_list")
    if not isinstance(packets, list):
        raise ValueError("packets_must_be_list")

    canonical_candidates: list[dict[str, Any]] = []
    by_candidate: dict[str, dict[str, Any]] = {}
    for raw in deepcopy(candidates):
        canonical = canonicalize(raw, source_commit=commit)
        cid = _required_text(canonical.get("candidate_id"), "candidate_id_required")
        if cid in by_candidate:
            raise ValueError(f"duplicate_candidate_id:{cid}")
        by_candidate[cid] = canonical
        canonical_candidates.append(canonical)

    packet_map = _packet_by_role(deepcopy(packets))
    tasks = packets_to_tasks(deepcopy(packets), hour)
    scheduled = schedule(tasks)
    decisions = _decision_map(scheduled)

    cases: list[dict[str, Any]] = []
    for candidate_id in sorted(by_candidate):
        task = _representative_task(tasks, decisions, candidate_id)
        if task is None:
            continue
        role = _required_text(task.get("legacy_role"), "legacy_role_required")
        packet = packet_map.get(role)
        if packet is None:
            raise ValueError(f"representative_packet_missing:{role}")
        identity = _case_identity(hour, candidate_id, task)
        task_id = identity["representative_task_id"]
        scheduler_decision = decisions.get(task_id)
        if scheduler_decision is None:
            raise ValueError(f"scheduler_decision_missing:{task_id}")

        candidate = by_candidate[candidate_id]
        case = {
            "case_id": _case_id(identity),
            "active_hour_id": hour,
            "candidate_id": candidate_id,
            "task_shape": identity["task_shape"],
            "representative_task_id": task_id,
            "legacy_role": role,
            "ground_truth": {
                "status": "UNRESOLVED",
                "ground_truth_class": None,
                "basis_refs": [],
            },
            "baseline_capture": _baseline_snapshot(packet, task),
            "challenger_capture": {
                "scheduler_decision": scheduler_decision["decision"],
                "scheduler_reason": scheduler_decision["reason"],
                "task_state": task.get("state"),
                "worker_domain": task.get("worker_domain"),
                "task_hash": _sha256(task),
            },
            "candidate_capture": {
                "phase": candidate.get("phase"),
                "queue_status": candidate.get("queue_status"),
                "economic_status": candidate.get("economic_status"),
                "candidate_hash": _sha256(candidate),
            },
        }
        cases.append(case)

    cycle_core = {
        "schema_version": CAPTURE_SCHEMA_VERSION,
        "mode": "PROSPECTIVE_SHADOW_CAPTURE",
        "active_hour_id": hour,
        "source_commit": commit,
        "candidate_input_count": len(canonical_candidates),
        "packet_input_count": len(packets),
        "task_input_count": len(tasks),
        "case_count": len(cases),
        "cases": cases,
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "runtime_mutation": False,
        "economic_conclusion": "NO_PROVEN_EDGE",
    }
    return {**cycle_core, "capture_hash": _sha256(cycle_core)}


def validate_cycle_capture(cycle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(cycle, dict):
        return ["cycle_must_be_object"]
    if cycle.get("schema_version") != CAPTURE_SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if cycle.get("mode") != "PROSPECTIVE_SHADOW_CAPTURE":
        errors.append("mode_mismatch")
    for key in ("active_hour_id", "source_commit", "capture_hash"):
        value = cycle.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{key}_required")
    for key in ("live_trading", "paid_actions", "wallet_actions", "runtime_mutation"):
        if cycle.get(key) is not False:
            errors.append(f"{key}_must_be_false")
    if cycle.get("economic_conclusion") != "NO_PROVEN_EDGE":
        errors.append("economic_conclusion_must_be_no_proven_edge")

    cases = cycle.get("cases")
    if not isinstance(cases, list):
        errors.append("cases_must_be_list")
        return errors
    if cycle.get("case_count") != len(cases):
        errors.append("case_count_mismatch")

    seen: set[str] = set()
    candidate_ids: set[str] = set()
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            errors.append(f"case_must_be_object:{index}")
            continue
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id.startswith(CASE_PREFIX + "-"):
            errors.append(f"case_id_invalid:{index}")
        elif case_id in seen:
            errors.append(f"duplicate_case_id:{case_id}")
        else:
            seen.add(case_id)
        cid = case.get("candidate_id")
        if not isinstance(cid, str) or not cid.strip():
            errors.append(f"candidate_id_invalid:{index}")
        elif cid in candidate_ids:
            errors.append(f"duplicate_candidate_event_in_cycle:{cid}")
        else:
            candidate_ids.add(cid)
        gt = case.get("ground_truth")
        if not isinstance(gt, dict) or gt.get("status") != "UNRESOLVED" or gt.get("ground_truth_class") is not None:
            errors.append(f"ground_truth_must_start_unresolved:{index}")

    supplied_hash = cycle.get("capture_hash")
    core = {key: value for key, value in cycle.items() if key != "capture_hash"}
    if isinstance(supplied_hash, str) and supplied_hash != _sha256(core):
        errors.append("capture_hash_mismatch")
    return sorted(set(errors))


def safe_cycle_filename(active_hour_id: str) -> str:
    text = _required_text(active_hour_id, "active_hour_id_required")
    stem = re.sub(r"[^A-Za-z0-9_.+-]+", "_", text).strip("._")
    if not stem:
        stem = "cycle"
    return f"{stem}-{_sha256(text)[:10]}.json"


def write_cycle_capture(output_dir: Path, cycle: dict[str, Any]) -> dict[str, Any]:
    errors = validate_cycle_capture(cycle)
    if errors:
        raise ValueError("invalid_cycle_capture:" + ",".join(errors))
    root = Path(output_dir)
    cycles_dir = root / "cycles"
    cycles_dir.mkdir(parents=True, exist_ok=True)
    path = cycles_dir / safe_cycle_filename(cycle["active_hour_id"])
    encoded = json.dumps(cycle, indent=2, sort_keys=True, ensure_ascii=False) + "\n"

    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing == encoded:
            return {"status": "IDEMPOTENT", "path": str(path), "capture_hash": cycle["capture_hash"]}
        raise ValueError(f"cycle_capture_conflict:{path}")

    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(encoded, encoding="utf-8")
    tmp.replace(path)
    return {"status": "CREATED", "path": str(path), "capture_hash": cycle["capture_hash"]}
