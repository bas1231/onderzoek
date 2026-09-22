from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .prospective_cohort import build_cohort_status
from .prospective_collector import build_cycle_capture
from .prospective_metrics import build_observation_set
from .prospective_pairing import build_paired_benchmark


ROOT = Path(__file__).resolve().parents[2]
BENCHMARKS = ROOT / "benchmarks" / "research_os_v1"
CONTROL = ROOT / "control" / "hourly"


class ValidationFailure(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def load_json(path: Path) -> dict[str, Any]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValidationFailure(f"invalid_json:{path}:{type(exc).__name__}") from exc
    if not isinstance(obj, dict):
        raise ValidationFailure(f"json_object_required:{path}")
    return obj


def _hour(index: int) -> str:
    start = datetime(2026, 9, 22, 0, 0, 0, tzinfo=timezone(timedelta(hours=2)))
    value = start + timedelta(hours=index)
    return "hourly-" + value.strftime("%Y%m%dT%H%M%S%z")


def _packet(role: str, candidate_id: str) -> dict[str, Any]:
    return {
        "agent_id": role,
        "status": "READY",
        "candidate_ids": [candidate_id],
        "input_refs": [f"synthetic/{candidate_id}.json"],
        "routed_evidence": [],
        "priority": "P2",
        "next_decisive_question": f"resolve {candidate_id}",
    }


def _candidates(index: int) -> list[dict[str, Any]]:
    survivor = {
        "candidate_id": "C-SURV",
        "hypothesis": "synthetic survivor",
        "phase": "MECHANISM_DEFINED",
        "queue_status": "WAITING_FOR_RESULT",
        "priority": "P1",
        "required_gates": {"mechanism": "PASS"},
        "next_decisive_question": "collect next prospective observation",
    }
    negative = {
        "candidate_id": "C-NEG",
        "hypothesis": "synthetic negative",
        "phase": "MECHANISM_DEFINED",
        "queue_status": "RUNNING",
        "priority": "P1",
        "required_gates": {"mechanism": "PENDING"},
        "next_decisive_question": "test mechanism",
    }
    # The cohort freezes after cycle 10. The next three cycles exist only to
    # resolve the frozen cases. Starting with the first post-cutoff cycle, C-NEG
    # becomes decisively negative while C-SURV continues with a progress signal.
    if index >= 10:
        negative["required_gates"] = {"mechanism": "FAIL"}
        negative["queue_status"] = "CLOSED_NEGATIVE"
        negative["economic_status"] = "TESTED_NEGATIVE"
    return [survivor, negative]


def _synthetic_cycles() -> list[dict[str, Any]]:
    cycles: list[dict[str, Any]] = []
    for index in range(13):
        cycles.append(
            build_cycle_capture(
                active_hour_id=_hour(index),
                source_commit="synthetic-source-commit",
                candidates=_candidates(index),
                packets=[
                    _packet("settlement", "C-SURV"),
                    _packet("algebra", "C-NEG"),
                ],
            )
        )
    return cycles


def _telemetry_record(
    meta: dict[str, Any],
    ground_truth: str,
    *,
    side: str,
) -> dict[str, Any]:
    better = side == "CHALLENGER"
    survivor = ground_truth == "SURVIVOR"
    record: dict[str, Any] = {
        **meta,
        "decision": "KEEP" if survivor else "KILL",
        "worker_run_ids": (
            [f"{meta['case_id']}:W1"]
            if better
            else [f"{meta['case_id']}:W1", f"{meta['case_id']}:W2"]
        ),
        "evidence": [
            {
                "evidence_id": f"{meta['case_id']}:E1",
                "source_family": "OFFICIAL",
                "relevant": True,
                "contradiction": not survivor,
                "point_in_time_ok": True,
                "provenance_ok": True,
            },
            {
                "evidence_id": f"{meta['case_id']}:E2",
                "source_family": "CODE",
                "relevant": True,
                "contradiction": False,
                "point_in_time_ok": True,
                "provenance_ok": True,
            },
        ],
        "research_items": [
            {"item_id": f"{meta['case_id']}:R1", "duplicate_of": None},
            {
                "item_id": f"{meta['case_id']}:R2",
                "duplicate_of": None if better else f"{meta['case_id']}:R1",
            },
        ],
        "failure_patterns": [
            {
                "pattern_id": "FP-001",
                "applicable": True,
                "detected_before_expensive_work": True,
            }
        ],
        "queue_starvation_event_ids": [],
        "hard_failures": [],
    }
    if not survivor:
        record["steps_to_decisive_falsification"] = 2
    return record


def _synthetic_benchmark(cohort: dict[str, Any]) -> dict[str, Any]:
    truth = {
        row["case_id"]: row["ground_truth_class"]
        for row in cohort["resolutions"]
    }
    baseline_records = [
        _telemetry_record(meta, truth[meta["case_id"]], side="BASELINE")
        for meta in cohort["cohort_case_metadata"]
    ]
    challenger_records = [
        _telemetry_record(meta, truth[meta["case_id"]], side="CHALLENGER")
        for meta in cohort["cohort_case_metadata"]
    ]
    baseline_raw = {
        "schema_version": 1,
        "side": "BASELINE",
        "cohort_hash": cohort["cohort_hash"],
        "records": baseline_records,
    }
    challenger_raw = {
        "schema_version": 1,
        "side": "CHALLENGER",
        "cohort_hash": cohort["cohort_hash"],
        "records": challenger_records,
    }
    baseline = build_observation_set(cohort, baseline_raw, "BASELINE")
    challenger = build_observation_set(cohort, challenger_raw, "CHALLENGER")
    return build_paired_benchmark(cohort, baseline, challenger)


def run_validation() -> dict[str, Any]:
    errors: list[str] = []
    details: dict[str, Any] = {}
    try:
        collection_policy = load_json(BENCHMARKS / "prospective_collection_policy.json")
        observation_policy = load_json(BENCHMARKS / "prospective_observation_policy.json")
        exchange_policy = load_json(BENCHMARKS / "exchange_telemetry_policy.json")
        challenger_policy = load_json(BENCHMARKS / "prospective_challenger_policy.json")
        worker_contract = load_json(CONTROL / "scheduled_worker_contract.json")

        require(
            collection_policy.get("status") == "PREREGISTERED_BEFORE_FIRST_PROSPECTIVE_CAPTURE",
            "collection_policy_not_preregistered",
        )
        require(
            observation_policy.get("status") == "FROZEN_BEFORE_FIRST_PROSPECTIVE_BENCHMARK_CASE",
            "observation_policy_not_frozen",
        )
        require(
            exchange_policy.get("status") == "FROZEN_BEFORE_FIRST_PROSPECTIVE_EXCHANGE_CASE",
            "exchange_policy_not_frozen",
        )
        require(
            challenger_policy.get("status") == "FROZEN_BEFORE_FIRST_PROSPECTIVE_EXCHANGE_CASE",
            "challenger_policy_not_frozen",
        )
        require(challenger_policy.get("maximum_logical_role_units") == 4, "challenger_role_cap_not_four")
        require(
            challenger_policy.get("resource_rule", {}).get("extra_scheduled_turns") == 0,
            "challenger_requires_extra_scheduled_turn",
        )

        instrumentation = worker_contract.get("prospective_shadow_telemetry")
        require(isinstance(instrumentation, dict), "main_instrumentation_missing")
        require(
            instrumentation.get("status") == "ENABLED_INSTRUMENTATION_ONLY",
            "main_instrumentation_not_enabled",
        )
        require(instrumentation.get("decision_behavior_change") is False, "instrumentation_changes_decisions")
        require(instrumentation.get("extra_scheduled_turns") == 0, "instrumentation_extra_turns_nonzero")
        require(instrumentation.get("candidate_authority_unchanged") is True, "instrumentation_changes_candidate_authority")
        require(instrumentation.get("economic_conclusion") == "NO_PROVEN_EDGE", "instrumentation_economic_default_changed")

        cycles = _synthetic_cycles()
        cohort = build_cohort_status(cycles)
        require(cohort.get("cohort_frozen") is True, "synthetic_cohort_not_frozen")
        require(cohort.get("cohort_cycle_count") == 10, "synthetic_cutoff_not_first_ten_cycles")
        require(cohort.get("cohort_case_count") == 20, "synthetic_case_count_not_twenty")
        require(len(cohort.get("task_shapes_observed") or []) >= 2, "synthetic_task_shape_diversity_missing")
        require(cohort.get("unresolved_cases") == 0, "synthetic_ground_truth_unresolved")
        require(cohort.get("resolved_survivors", 0) >= 1, "synthetic_survivor_missing")
        require(cohort.get("resolved_decisive_negatives", 0) >= 1, "synthetic_negative_missing")
        require(
            cohort.get("replacement_benchmark_ready") is True,
            "synthetic_cohort_not_ready_for_pairing",
        )

        benchmark = _synthetic_benchmark(cohort)
        replacement = benchmark.get("replacement_check") or {}
        require(
            replacement.get("scientific_replacement_gate_met") is True,
            "synthetic_replacement_gate_should_pass",
        )
        require(
            benchmark.get("automatic_runtime_replacement_authorized") is False,
            "benchmark_auto_authorizes_runtime",
        )
        require(
            benchmark.get("requires_human_integration_decision") is True,
            "benchmark_missing_human_integration_gate",
        )
        require(benchmark.get("economic_conclusion") == "NO_PROVEN_EDGE", "benchmark_economic_default_changed")

        details = {
            "synthetic_cycles": len(cycles),
            "cohort_cycle_count": cohort.get("cohort_cycle_count"),
            "cohort_case_count": cohort.get("cohort_case_count"),
            "resolved_survivors": cohort.get("resolved_survivors"),
            "resolved_decisive_negatives": cohort.get("resolved_decisive_negatives"),
            "task_shapes_observed": cohort.get("task_shapes_observed"),
            "strict_improvements": replacement.get("strict_improvements"),
            "scientific_replacement_gate_met": replacement.get("scientific_replacement_gate_met"),
        }
    except Exception as exc:
        errors.append(f"{type(exc).__name__}:{exc}")

    return {
        "validator": "RESEARCH_OS_V1_PROSPECTIVE_READY",
        "status": "PASS" if not errors else "FAIL_CLOSED",
        "errors": errors,
        "details": details,
        "first_prospective_datapoint_authorized": not errors,
        "automatic_runtime_replacement_authorized": False,
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "runtime_mutation": False,
        "network_calls": False,
        "economic_conclusion": "NO_PROVEN_EDGE",
    }


if __name__ == "__main__":
    result = run_validation()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASS" else 1)
