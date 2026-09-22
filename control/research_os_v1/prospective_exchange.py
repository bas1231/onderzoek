from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

from .candidate_view import canonicalize
from .legacy_adapter import packet_to_task
from .prospective_collector import task_shape_label
from .scheduler import schedule


EXCHANGE_BUNDLE_SCHEMA_VERSION = 1
KILLER_ROLES = {"prebuild_killer", "chief_falsifier"}
FIXED_DISCOVERY_ROLES = ("scout", "recon_scout")
DIRECTOR_ROLE = "research_director"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _text(value: Any, error: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(error)
    return value.strip()


def _false_flag(value: Any, error: str) -> None:
    if value in {True, "true", "TRUE", 1}:
        raise ValueError(error)


def _validate_exchange_pair(
    request: dict[str, Any], response_envelope: dict[str, Any]
) -> dict[str, Any]:
    if not isinstance(request, dict) or request.get("schema") != "PVA_AI_EXCHANGE_REQUEST_V1":
        raise ValueError("invalid_exchange_request")
    if not isinstance(response_envelope, dict) or response_envelope.get("schema") != "PVA_AI_EXCHANGE_RESPONSE_V1":
        raise ValueError("invalid_exchange_response_envelope")

    run_id = _text(request.get("run_id"), "request_run_id_required")
    if response_envelope.get("run_id") != run_id:
        raise ValueError("exchange_run_id_mismatch")
    request_sha = _text(request.get("request_sha256"), "request_sha256_required")
    if response_envelope.get("request_sha256") != request_sha:
        raise ValueError("exchange_request_sha256_mismatch")

    response = response_envelope.get("response")
    if not isinstance(response, dict) or response.get("schema") != "PVA_AI_RESPONSE_V1":
        raise ValueError("invalid_worker_response")
    if response.get("run_id") != run_id:
        raise ValueError("worker_response_run_id_mismatch")
    if response.get("response_token") != request.get("response_token"):
        raise ValueError("worker_response_token_mismatch")
    if response.get("economic_conclusion") != "NO_PROVEN_EDGE":
        raise ValueError("economic_conclusion_must_be_no_proven_edge")

    for key in ("live_trading", "paid_actions", "wallet_actions", "openai_api"):
        _false_flag(response.get(key), f"forbidden_response_flag:{key}")
    governor = request.get("governor")
    if not isinstance(governor, dict):
        raise ValueError("request_governor_required")
    for key in ("live_trading", "paid_actions", "wallet_actions", "openai_api"):
        _false_flag(governor.get(key), f"forbidden_request_flag:{key}")

    work_items = request.get("work_items")
    role_results = response.get("role_results")
    if not isinstance(work_items, list) or not isinstance(role_results, list):
        raise ValueError("work_items_and_role_results_required")

    expected_roles: list[str] = []
    seen_expected: set[str] = set()
    for index, item in enumerate(work_items):
        if not isinstance(item, dict):
            raise ValueError(f"work_item_must_be_object:{index}")
        role = _text(item.get("agent_id"), f"work_item_agent_id_required:{index}")
        if role in seen_expected:
            raise ValueError(f"duplicate_work_item_role:{role}")
        seen_expected.add(role)
        if item.get("must_return_result") is not False:
            expected_roles.append(role)

    result_roles: list[str] = []
    seen_results: set[str] = set()
    for index, result in enumerate(role_results):
        if not isinstance(result, dict):
            raise ValueError(f"role_result_must_be_object:{index}")
        role = _text(result.get("agent_id"), f"role_result_agent_id_required:{index}")
        if role in seen_results:
            raise ValueError(f"duplicate_role_result:{role}")
        seen_results.add(role)
        result_roles.append(role)
        if not isinstance(result.get("benchmark_telemetry"), dict):
            raise ValueError(f"benchmark_telemetry_missing:{role}")

    if set(result_roles) != set(expected_roles):
        missing = sorted(set(expected_roles) - set(result_roles))
        extra = sorted(set(result_roles) - set(expected_roles))
        raise ValueError(
            "role_coverage_mismatch:"
            f"missing={','.join(missing)}:extra={','.join(extra)}"
        )
    return response


def _request_tasks(request: dict[str, Any]) -> list[dict[str, Any]]:
    run_id = _text(request.get("run_id"), "request_run_id_required")
    tasks: list[dict[str, Any]] = []
    for index, work_item in enumerate(request.get("work_items") or []):
        if not isinstance(work_item, dict):
            raise ValueError(f"work_item_must_be_object:{index}")
        role = _text(work_item.get("agent_id"), f"work_item_agent_id_required:{index}")
        packet = work_item.get("packet")
        if not isinstance(packet, dict):
            raise ValueError(f"work_item_packet_required:{role}")
        packet = deepcopy(packet)
        # Inclusion in work_items is the point-in-time legacy-orchestrator READY
        # decision. Force READY so the challenger can only choose among roles
        # the baseline already released; it cannot invent new work.
        packet["status"] = "READY"
        if packet.get("agent_id") != role:
            raise ValueError(f"work_item_packet_role_mismatch:{role}")
        if not packet.get("objective") and work_item.get("objective") is not None:
            packet["objective"] = work_item.get("objective")
        task = packet_to_task(packet, run_id)
        if task is None:
            raise ValueError(f"unsupported_request_role:{role}")
        tasks.append(task)
    return tasks


def select_challenger_roles(request: dict[str, Any]) -> list[str]:
    """Frozen CANARY_LOW_USAGE logical-role selection.

    Scout + Recon are protected, one dynamic role is selected by the ordinal
    scheduler, and Director is protected. All roles must already exist in the
    pre-response request.
    """
    tasks = _request_tasks(request)
    by_role = {task["legacy_role"]: task for task in tasks}
    selected: list[str] = []

    for role in FIXED_DISCOVERY_ROLES:
        task = by_role.get(role)
        if task is None:
            continue
        decision = schedule([task], max_tasks=1)
        if decision["selected"]:
            selected.append(role)

    dynamic_tasks = [
        task
        for task in tasks
        if task["legacy_role"] not in {*FIXED_DISCOVERY_ROLES, DIRECTOR_ROLE}
    ]
    if dynamic_tasks:
        dynamic = schedule(dynamic_tasks, max_tasks=1)
        if dynamic["tasks"]:
            selected.append(dynamic["tasks"][0]["legacy_role"])

    director = by_role.get(DIRECTOR_ROLE)
    if director is not None:
        decision = schedule([director], max_tasks=1)
        if decision["selected"]:
            selected.append(DIRECTOR_ROLE)

    if len(selected) > 4:
        raise ValueError("challenger_role_cap_exceeded")
    return selected


def _candidate_ids_from_tasks(tasks: list[dict[str, Any]]) -> list[str]:
    ids: set[str] = set()
    for task in tasks:
        inputs = task.get("inputs")
        if not isinstance(inputs, dict):
            continue
        values = inputs.get("candidate_ids")
        if not isinstance(values, list):
            continue
        for value in values:
            if isinstance(value, str) and value.strip():
                ids.add(value.strip())
    return sorted(ids)


def _representative_task(
    linked: list[dict[str, Any]], selected_roles: set[str]
) -> dict[str, Any]:
    if not linked:
        raise ValueError("linked_task_required")
    return min(
        linked,
        key=lambda task: (
            0 if task.get("legacy_role") in selected_roles else 1,
            _text(task.get("task_id"), "task_id_required"),
        ),
    )


def _case_identity(run_id: str, candidate_id: str, task: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "active_hour_id": run_id,
        "candidate_id": candidate_id,
        "representative_task_id": _text(task.get("task_id"), "task_id_required"),
        "legacy_role": _text(task.get("legacy_role"), "legacy_role_required"),
        "task_shape": task_shape_label(task),
    }


def _case_id(identity: dict[str, Any]) -> str:
    return f"ROS1-{_sha256(identity)[:24]}"


def _result_map(response: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for result in response["role_results"]:
        role = result["agent_id"]
        out[role] = result
    return out


def _merge_dict_items(
    rows: list[dict[str, Any]], key: str, context: str
) -> list[dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        ident = _text(row.get(key), f"{context}_{key}_required")
        existing = out.get(ident)
        if existing is None:
            out[ident] = deepcopy(row)
        elif existing != row:
            raise ValueError(f"{context}_conflict:{ident}")
    return [out[key_] for key_ in sorted(out)]


def _aggregate_role_telemetry(
    case_identity: dict[str, Any],
    role_results: list[dict[str, Any]],
    *,
    side: str,
    intentionally_unassigned: bool = False,
) -> dict[str, Any]:
    if intentionally_unassigned:
        return {
            **case_identity,
            "decision": "KEEP",
            "intentionally_unassigned": True,
            "worker_run_ids": [],
            "evidence": [],
            "research_items": [],
            "failure_patterns": [],
            "queue_starvation_event_ids": [],
            "hard_failures": [],
        }

    worker_ids: list[str] = []
    evidence_rows: list[dict[str, Any]] = []
    research_rows: list[dict[str, Any]] = []
    failure_rows: list[dict[str, Any]] = []
    starvation_ids: set[str] = set()
    hard_failures: set[str] = set()
    overhead_values: list[float] = []
    usage_values: list[float] = []
    overhead_complete = True
    usage_complete = True
    kill_step: int | None = None

    for step, result in enumerate(role_results, start=1):
        telemetry = result.get("benchmark_telemetry")
        if not isinstance(telemetry, dict):
            raise ValueError(f"benchmark_telemetry_missing:{result.get('agent_id')}")
        worker_id = _text(
            telemetry.get("worker_run_id"),
            f"worker_run_id_required:{result.get('agent_id')}",
        )
        if worker_id in worker_ids:
            raise ValueError(f"duplicate_worker_run_id:{worker_id}")
        worker_ids.append(worker_id)

        for key, target in (
            ("evidence", evidence_rows),
            ("research_items", research_rows),
            ("failure_patterns", failure_rows),
        ):
            values = telemetry.get(key)
            if not isinstance(values, list):
                raise ValueError(f"benchmark_telemetry_list_required:{result.get('agent_id')}:{key}")
            for value in values:
                if not isinstance(value, dict):
                    raise ValueError(f"benchmark_telemetry_item_object_required:{result.get('agent_id')}:{key}")
                target.append(deepcopy(value))

        qids = telemetry.get("queue_starvation_event_ids")
        if not isinstance(qids, list):
            raise ValueError(f"queue_starvation_event_ids_required:{result.get('agent_id')}")
        for qid in qids:
            starvation_ids.add(_text(qid, "queue_starvation_event_id_invalid"))

        failures = telemetry.get("hard_failures", [])
        if not isinstance(failures, list):
            raise ValueError(f"hard_failures_must_be_list:{result.get('agent_id')}")
        for failure in failures:
            hard_failures.add(_text(failure, "hard_failure_invalid"))

        for field, destination, completeness_name in (
            ("coordination_overhead_units", overhead_values, "overhead"),
            ("plan_usage_units", usage_values, "usage"),
        ):
            value = telemetry.get(field)
            if value is None:
                if completeness_name == "overhead":
                    overhead_complete = False
                else:
                    usage_complete = False
            elif not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
                raise ValueError(f"invalid_benchmark_unit:{result.get('agent_id')}:{field}")
            else:
                destination.append(float(value))

        role = result.get("agent_id")
        if role in KILLER_ROLES and result.get("status") == "FALSIFIED" and kill_step is None:
            kill_step = step

    evidence = _merge_dict_items(evidence_rows, "evidence_id", "evidence")
    for item in evidence:
        eid = item.get("evidence_id")
        if isinstance(eid, str) and eid.startswith("ai_exchange/") and item.get("relevant") is not False:
            raise ValueError(f"transport_self_reference_must_be_irrelevant:{eid}")
    research = _merge_dict_items(research_rows, "item_id", "research_item")
    failures = _merge_dict_items(failure_rows, "pattern_id", "failure_pattern")

    record: dict[str, Any] = {
        **case_identity,
        "decision": "KILL" if kill_step is not None else "KEEP",
        "intentionally_unassigned": False,
        "worker_run_ids": worker_ids,
        "evidence": evidence,
        "research_items": research,
        "failure_patterns": failures,
        "queue_starvation_event_ids": sorted(starvation_ids),
        "hard_failures": sorted(hard_failures),
    }
    if kill_step is not None:
        record["steps_to_decisive_falsification"] = kill_step
    if overhead_complete and overhead_values:
        record["coordination_overhead_units"] = round(sum(overhead_values), 6)
    if usage_complete and usage_values:
        record["plan_usage_units"] = round(sum(usage_values), 6)
    return record


def build_exchange_shadow_bundle(
    request: dict[str, Any],
    response_envelope: dict[str, Any],
    candidate_records: list[dict[str, Any]],
) -> dict[str, Any]:
    response = _validate_exchange_pair(request, response_envelope)
    run_id = request["run_id"]
    source_commit = _text(request.get("source_commit"), "source_commit_required")
    tasks = _request_tasks(request)
    selected_roles = select_challenger_roles(request)
    selected_set = set(selected_roles)
    results = _result_map(response)

    candidate_map: dict[str, dict[str, Any]] = {}
    for raw in deepcopy(candidate_records):
        canonical = canonicalize(raw, source_commit=source_commit)
        cid = _text(canonical.get("candidate_id"), "candidate_id_required")
        if cid in candidate_map:
            raise ValueError(f"duplicate_candidate_record:{cid}")
        candidate_map[cid] = canonical

    case_candidates = _candidate_ids_from_tasks(tasks)
    missing_records = sorted(set(case_candidates) - set(candidate_map))
    if missing_records:
        raise ValueError("missing_candidate_records:" + ",".join(missing_records))

    cases: list[dict[str, Any]] = []
    baseline_records: list[dict[str, Any]] = []
    challenger_records: list[dict[str, Any]] = []

    for candidate_id in case_candidates:
        linked_tasks = [
            task
            for task in tasks
            if candidate_id in (task.get("inputs") or {}).get("candidate_ids", [])
        ]
        representative = _representative_task(linked_tasks, selected_set)
        identity_core = _case_identity(run_id, candidate_id, representative)
        case_id = _case_id(identity_core)
        case_identity = {
            "case_id": case_id,
            "active_hour_id": run_id,
            "candidate_id": candidate_id,
            "task_shape": identity_core["task_shape"],
            "representative_task_id": identity_core["representative_task_id"],
            "legacy_role": identity_core["legacy_role"],
        }

        linked_roles = [task["legacy_role"] for task in linked_tasks]
        baseline_role_results: list[dict[str, Any]] = []
        challenger_role_results: list[dict[str, Any]] = []
        for role in linked_roles:
            result = results.get(role)
            if result is None:
                raise ValueError(f"candidate_linked_role_result_missing:{candidate_id}:{role}")
            candidate_ids = result.get("candidate_ids")
            if not isinstance(candidate_ids, list) or candidate_id not in candidate_ids:
                raise ValueError(f"candidate_link_missing_in_result:{candidate_id}:{role}")
            baseline_role_results.append(result)
            if role in selected_set:
                challenger_role_results.append(result)

        baseline_records.append(
            _aggregate_role_telemetry(case_identity, baseline_role_results, side="BASELINE")
        )
        challenger_records.append(
            _aggregate_role_telemetry(
                case_identity,
                challenger_role_results,
                side="CHALLENGER",
                intentionally_unassigned=not challenger_role_results,
            )
        )

        candidate = candidate_map[candidate_id]
        cases.append({
            **case_identity,
            "ground_truth": {
                "status": "UNRESOLVED",
                "ground_truth_class": None,
                "basis_refs": [],
            },
            "baseline_capture": {
                "linked_roles": sorted(linked_roles),
                "linked_role_count": len(linked_roles),
            },
            "challenger_capture": {
                "selected_roles": [role for role in selected_roles if role in linked_roles],
                "intentionally_unassigned": not challenger_role_results,
            },
            "candidate_capture": {
                "phase": candidate.get("phase"),
                "queue_status": candidate.get("queue_status"),
                "economic_status": candidate.get("economic_status"),
                "required_gates": deepcopy(candidate.get("required_gates") or {}),
                "next_decisive_question": candidate.get("next_decisive_question"),
                "blockers": deepcopy(candidate.get("blockers") or []),
                "dependencies": deepcopy(candidate.get("dependencies") or []),
                "candidate_hash": _sha256(candidate),
            },
        })

    cycle_core = {
        "schema_version": 1,
        "mode": "PROSPECTIVE_SHADOW_CAPTURE",
        "active_hour_id": run_id,
        "source_commit": source_commit,
        "candidate_input_count": len(candidate_records),
        "packet_input_count": len(request.get("work_items") or []),
        "task_input_count": len(tasks),
        "case_count": len(cases),
        "cases": cases,
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "runtime_mutation": False,
        "economic_conclusion": "NO_PROVEN_EDGE",
    }
    cycle = {**cycle_core, "capture_hash": _sha256(cycle_core)}

    return {
        "schema_version": EXCHANGE_BUNDLE_SCHEMA_VERSION,
        "run_id": run_id,
        "source_commit": source_commit,
        "request_sha256": request["request_sha256"],
        "challenger_selected_roles": selected_roles,
        "cycle_capture": cycle,
        "baseline_records": baseline_records,
        "challenger_records": challenger_records,
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "runtime_mutation": False,
        "economic_conclusion": "NO_PROVEN_EDGE",
    }
