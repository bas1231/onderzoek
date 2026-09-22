from __future__ import annotations

import json
import py_compile
from pathlib import Path

from .candidate_view import canonicalize
from .contracts import validate_task
from .discovery_coverage import summarize as summarize_coverage
from .evidence_graph import EvidenceGraph
from .failure_memory import pattern_index
from .governor import classify
from .hypothesis_accounting import adaptive_search_flags, normalize as normalize_search_family
from .legacy_adapter import packet_to_task
from .promotion import evaluate as evaluate_promotion
from .red_team import build_blind_packet
from .reproducer import build_packet as build_reproducer_packet, source_independence
from .resurrection import evaluate as evaluate_resurrection
from .scheduler import fanout_cap, schedule
from .shadow_benchmark import summarize as summarize_benchmark, replacement_check

BASE = Path(__file__).resolve().parent

RUNTIME_FILES = [
    "__init__.py",
    "policy.py",
    "governor.py",
    "failure_memory.py",
    "candidate_view.py",
    "evidence_graph.py",
    "contracts.py",
    "scheduler.py",
    "shadow_cycle.py",
    "legacy_adapter.py",
    "shadow_cli.py",
    "hypothesis_accounting.py",
    "discovery_coverage.py",
    "promotion.py",
    "resurrection.py",
    "red_team.py",
    "reproducer.py",
    "shadow_benchmark.py",
]


def _valid_task(task_id: str = "SMOKE") -> dict:
    return {
        "task_id": task_id,
        "worker_domain": "discovery",
        "objective": "smoke test",
        "state": "READY",
        "task_shape": {
            "parallelism": "LOW",
            "dependency_shape": "SEQUENTIAL",
            "uncertainty_type": "SOURCE",
            "time_sensitivity": "LOW",
            "novelty": "INCREMENTAL",
            "decision_relevance": "LOW",
        },
        "inputs": {},
        "constraints": {
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
            "source_policy": "LOCAL_EXISTING_ONLY",
        },
        "expected_output": {
            "artifact_type": "DISCOVERY_FINDING",
            "required_fields": ["evidence"],
        },
        "scheduling": {
            "uncertainty_reduction": "LOW",
            "dependency_unlock_value": "NONE",
            "evidence_cost": "LOW",
            "model_cost": "LOW",
            "duplication_risk": "LOW",
        },
        "proposed_action": {
            "kind": "free_public_read_only_research",
            "provenance": True,
            "point_in_time": True,
        },
    }


def _benchmark_rows(*, better: bool = False, case_prefix: str = "CASE") -> list[dict]:
    rows = []
    for i in range(20):
        cls = "SURVIVOR" if i == 0 else "DECISIVE_NEGATIVE"
        rows.append({
            "case_id": f"{case_prefix}-{i:02d}",
            "active_hour_id": f"H{i // 2}",
            "task_shape": "PARALLEL" if i % 2 else "SEQUENTIAL",
            "ground_truth_class": cls,
            "decision": "KEEP" if cls == "SURVIVOR" else "KILL",
            "worker_runs": 2,
            "unique_relevant_evidence": 3 if better else 2,
            "research_items": 3,
            "duplicate_research_items": 0 if better else 1,
            "contradictions_found": 1,
            "applicable_known_failure_patterns": 1,
            "failure_patterns_before_expensive_work": 1,
            "point_in_time_and_provenance_complete": True,
            "queue_starvation_events": 0,
            "steps_to_decisive_falsification": 2,
            "source_families_covered": ["OFFICIAL", "CODE"],
            "hard_failures": [],
        })
    return rows


def main() -> int:
    errors: list[str] = []

    for name in RUNTIME_FILES:
        path = BASE / name
        if not path.is_file():
            errors.append(f"MISSING_RUNTIME_FILE:{name}")
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:
            errors.append(f"COMPILE_FAIL:{name}:{exc}")

    try:
        patterns = pattern_index()
        if len(patterns) < 30:
            errors.append(f"FAILURE_MEMORY_TOO_SMALL:{len(patterns)}")
        malformed_memory = {
            "schema_version": 1,
            "patterns": [{
                "id": "FP-X",
                "name": "x",
                "gate": 123,
                "trigger": "x",
                "required_check": "x",
                "default_effect": "BLOCK",
            }],
        }
        try:
            pattern_index(malformed_memory)
            errors.append("FAILURE_MEMORY_STRINGIFIED_NON_STRING_FIELD")
        except ValueError:
            pass
    except Exception as exc:
        errors.append(f"FAILURE_MEMORY_LOAD_FAIL:{exc}")

    try:
        if classify({"kind": "magic_unknown_action"}).admissible:
            errors.append("GOVERNOR_UNKNOWN_ACTION_NOT_BLOCKED")
        if not classify({"kind": "paid_action"}).requires_user_approval:
            errors.append("GOVERNOR_PAID_ACTION_NOT_APPROVAL_GATED")
        if not classify({"kind": "live_order_or_trade"}).requires_user_approval:
            errors.append("GOVERNOR_LIVE_ACTION_NOT_APPROVAL_GATED")
        if not classify({"kind": "wallet_or_fund_movement"}).requires_user_approval:
            errors.append("GOVERNOR_WALLET_ACTION_NOT_APPROVAL_GATED")
    except Exception as exc:
        errors.append(f"GOVERNOR_SMOKE_FAIL:{exc}")

    try:
        candidate = canonicalize(
            {"candidate_id": "SMOKE", "hypothesis": "h", "decision": "UNPROVEN", "gates": {}},
            source_commit="smoke",
        )
        if candidate["economic_status"] != "NO_PROVEN_EDGE":
            errors.append("CANDIDATE_DEFAULT_NOT_NO_PROVEN_EDGE")

        canonical = canonicalize(
            {
                "candidate_id": "SMOKE-CANON",
                "hypothesis": "h",
                "required_gates": {"mechanism": "PASS", "execution_reality": "FAIL"},
                "gates": {},
                "queue_status": "CLOSED_NEGATIVE",
            },
            source_commit="smoke",
        )
        if canonical["required_gates"].get("execution_reality") != "FAIL":
            errors.append("CANONICAL_GATE_STATE_LOST")
        if canonical.get("economic_status") != "TESTED_NEGATIVE":
            errors.append("CLOSED_NEGATIVE_STATE_LOST")
    except Exception as exc:
        errors.append(f"CANDIDATE_SMOKE_FAIL:{exc}")

    try:
        valid = _valid_task()
        if validate_task(valid):
            errors.append("VALID_TASK_REJECTED")
        if fanout_cap(valid) != 1:
            errors.append("SEQUENTIAL_FANOUT_NOT_ONE")
        if schedule([valid]).get("selected") != ["SMOKE"]:
            errors.append("VALID_READY_TASK_NOT_SCHEDULED")

        malformed = _valid_task("MALFORMED")
        malformed.pop("proposed_action")
        malformed_plan = schedule([malformed])
        if malformed_plan.get("selected"):
            errors.append("MALFORMED_TASK_SCHEDULED")
        if not malformed_plan.get("blocked") or malformed_plan["blocked"][0].get("decision") != "BLOCK_INVALID_CONTRACT":
            errors.append("MALFORMED_TASK_NOT_CONTRACT_BLOCKED")

        blocked_task = _valid_task("BLOCKED")
        blocked_task["state"] = "BLOCKED"
        blocked_plan = schedule([blocked_task])
        if blocked_plan.get("selected"):
            errors.append("BLOCKED_STATE_TASK_SCHEDULED")
    except Exception as exc:
        errors.append(f"SCHEDULER_CONTRACT_SMOKE_FAIL:{exc}")

    try:
        unknown_status = packet_to_task(
            {"agent_id": "settlement", "status": "MYSTERY_STATE", "input_refs": ["x"]},
            "SMOKE-RUN",
        )
        if unknown_status is None or unknown_status.get("state") != "BLOCKED":
            errors.append("UNKNOWN_LEGACY_STATUS_NOT_BLOCKED")
        if unknown_status is not None and schedule([unknown_status]).get("selected"):
            errors.append("UNKNOWN_LEGACY_STATUS_SCHEDULED")
    except Exception as exc:
        errors.append(f"LEGACY_ADAPTER_SMOKE_FAIL:{exc}")

    try:
        node = {
            "id": "e1",
            "type": "evidence",
            "status": "OK",
            "created_at": "2026-09-21T00:00:00Z",
            "producer": "smoke",
        }
        try:
            EvidenceGraph({
                "schema_version": 1,
                "nodes": [node, {**node, "status": "CONFLICT"}],
                "edges": [],
            })
            errors.append("CONFLICTING_GRAPH_NODE_ACCEPTED")
        except ValueError as exc:
            if "conflicting_node" not in str(exc):
                errors.append(f"GRAPH_CONFLICT_WRONG_FAILURE:{exc}")
    except Exception as exc:
        errors.append(f"EVIDENCE_GRAPH_SMOKE_FAIL:{exc}")

    try:
        flags = adaptive_search_flags({
            "id": "SMOKE",
            "hypotheses_examined": 2,
            "parameterizations_examined": 0,
            "post_hoc_mutations": 0,
            "untouched_evidence_remaining": True,
        })
        if flags.get("discovery_evidence_may_promote_directly") is not False:
            errors.append("ADAPTIVE_SEARCH_NOT_DOWNGRADED")

        try:
            normalize_search_family({
                "id": "BADBOOL",
                "hypotheses_examined": 1,
                "parameterizations_examined": 0,
                "post_hoc_mutations": 0,
                "untouched_evidence_remaining": "false",
            })
            errors.append("STRING_BOOLEAN_ACCEPTED_IN_SEARCH_ACCOUNTING")
        except ValueError:
            pass
    except Exception as exc:
        errors.append(f"HYPOTHESIS_ACCOUNTING_SMOKE_FAIL:{exc}")

    try:
        zero = summarize_coverage([], [], [], [])
        if zero.get("primary_source_ratio") is not None or zero.get("duplicate_cross_scout_ratio") is not None:
            errors.append("ZERO_DISCOVERY_DENOMINATOR_NOT_UNKNOWN")

        mirrored = summarize_coverage(
            [{"source_id": "a", "document_sha256": "ABC", "source_family": "official", "retrieval_succeeded": True}],
            [{"source_id": "b", "document_sha256": "abc", "source_family": "community", "retrieval_succeeded": True}],
            ["official"],
            ["official"],
        )
        if mirrored.get("duplicate_cross_scout_keys") != 1:
            errors.append("MIRRORED_CONTENT_NOT_DEDUPED")
    except Exception as exc:
        errors.append(f"DISCOVERY_COVERAGE_SMOKE_FAIL:{exc}")

    try:
        gates = {
            g: "PASS"
            for g in [
                "source_provenance", "point_in_time", "mechanism", "signal_edge",
                "market_edge", "execution_reality", "prebuild_killer",
                "chief_falsifier", "validation", "holdout",
                "independent_reproduction", "shadow",
            ]
        }
        verdict = evaluate_promotion({"required_gates": gates})
        if verdict.get("status") != "PROMOTION_CANDIDATE":
            errors.append("FULL_PROMOTION_GATE_SET_NOT_RECOGNIZED")
        if verdict.get("live_trading_authorized") is not False:
            errors.append("PROMOTION_AUTHORIZED_LIVE_TRADING")

        missing_holdout = dict(gates)
        missing_holdout.pop("holdout")
        holdout_verdict = evaluate_promotion({"required_gates": missing_holdout})
        if holdout_verdict.get("eligible") is not False or "holdout" not in holdout_verdict.get("pending_gates", []):
            errors.append("PROMOTION_DID_NOT_REQUIRE_HOLDOUT")

        no_signal_gates = dict(gates)
        no_signal_gates["signal_edge"] = "PENDING"
        no_signal = evaluate_promotion({"required_gates": no_signal_gates}, signal_required=False)
        if no_signal.get("eligible") is not False:
            errors.append("NO_SIGNAL_ROUTE_SKIPPED_UNRESOLVED_SIGNAL_GATE")
    except Exception as exc:
        errors.append(f"PROMOTION_SMOKE_FAIL:{exc}")

    try:
        blind = build_blind_packet({
            "candidate_id": "BLIND",
            "hypothesis": "h",
            "claims": [],
            "assumptions": [],
            "supporting_evidence": [],
            "contradictory_evidence": [],
            "required_gates": {"mechanism": "PASS", "market_edge": "FAIL"},
            "known_failure_patterns": [],
        })
        if set(blind.get("required_gates", {}).values()) != {"UNKNOWN"}:
            errors.append("RED_TEAM_ORIGIN_GATE_STATE_LEAK")
        if blind.get("origin_gate_states_included") is not False:
            errors.append("RED_TEAM_GATE_STATE_BLINDING_FLAG_WRONG")
    except Exception as exc:
        errors.append(f"RED_TEAM_BLINDING_SMOKE_FAIL:{exc}")

    try:
        same = source_independence(["same"], ["same"])
        if same.get("counts_as_independent_reproduction") is not False:
            errors.append("SHARED_SOURCE_COUNTED_AS_INDEPENDENT")
        opaque = source_independence(["derived:a"], ["derived:b"])
        if opaque.get("status") != "UNKNOWN":
            errors.append("OPAQUE_DERIVED_REFS_COUNTED_AS_SOURCE_INDEPENDENCE")
        explicit = source_independence(
            [{"ref": "a", "upstream_source_ids": ["source:a"]}],
            [{"ref": "b", "upstream_source_ids": ["source:b"]}],
        )
        if explicit.get("counts_as_independent_reproduction") is not True:
            errors.append("EXPLICIT_DISJOINT_LINEAGE_NOT_RECOGNIZED")
        try:
            source_independence([123], [{"ref": "b", "upstream_source_ids": ["source:b"]}])
            errors.append("REPRODUCER_ACCEPTED_NON_REFERENCE_ITEM")
        except ValueError:
            pass
        try:
            build_reproducer_packet(
                {"candidate_id": "R", "supporting_evidence": "raw/a.json"},
                "question",
            )
            errors.append("REPRODUCER_ACCEPTED_STRING_AS_EVIDENCE_LIST")
        except ValueError:
            pass
    except Exception as exc:
        errors.append(f"REPRODUCTION_SMOKE_FAIL:{exc}")

    try:
        resurrected = evaluate_resurrection(
            {
                "candidate_id": "R",
                "queue_status": "CLOSED_NEGATIVE",
                "economic_status": "TESTED_NEGATIVE",
                "resurrection_conditions": ["regime_change"],
                "required_gates": {"source_provenance": "PASS", "mechanism": "PASS"},
            },
            ["regime_change"],
            "2026-09-21T00:00:00Z",
        )
        if resurrected["candidate"]["required_gates"].get("source_provenance") != "PENDING":
            errors.append("RESURRECTION_INHERITED_OLD_PROVENANCE_PASS")
        try:
            evaluate_resurrection(
                {
                    "candidate_id": "R2",
                    "queue_status": "CLOSED_NEGATIVE",
                    "economic_status": "TESTED_NEGATIVE",
                    "resurrection_conditions": ["regime_change"],
                },
                "regime_change",
                "2026-09-21T00:00:00Z",
            )
            errors.append("RESURRECTION_ACCEPTED_STRING_AS_CHANGED_CONDITION_LIST")
        except ValueError:
            pass
    except Exception as exc:
        errors.append(f"RESURRECTION_SMOKE_FAIL:{exc}")

    try:
        baseline_rows = _benchmark_rows()
        challenger_rows = _benchmark_rows(better=True)
        baseline = summarize_benchmark(baseline_rows)
        challenger = summarize_benchmark(challenger_rows)
        replacement = replacement_check(baseline, challenger)
        if replacement.get("scientific_replacement_gate_met") is not True:
            errors.append("MATCHED_BENCHMARK_REPLACEMENT_CHECK_FAILED")

        mismatched = summarize_benchmark(_benchmark_rows(better=True, case_prefix="OTHER"))
        mismatch_verdict = replacement_check(baseline, mismatched)
        if mismatch_verdict.get("scientific_replacement_gate_met") is not False:
            errors.append("MISMATCHED_CASE_SET_ALLOWED_REPLACEMENT")

        relabelled_rows = _benchmark_rows(better=True)
        relabelled_rows[1]["ground_truth_class"] = "SURVIVOR"
        relabelled_rows[1]["decision"] = "KEEP"
        relabelled = summarize_benchmark(relabelled_rows)
        relabelled_verdict = replacement_check(baseline, relabelled)
        if relabelled_verdict.get("comparable_case_metadata") is not False:
            errors.append("RELABELLED_CASE_METADATA_TREATED_AS_COMPARABLE")
        if relabelled_verdict.get("scientific_replacement_gate_met") is not False:
            errors.append("RELABELLED_CASE_ALLOWED_REPLACEMENT")

        malformed_numeric_rows = _benchmark_rows()
        malformed_numeric_rows[0]["worker_runs"] = "2"
        malformed_numeric = summarize_benchmark(malformed_numeric_rows)
        if not any(
            str(error).endswith(":worker_runs")
            for error in malformed_numeric.get("validation_errors", [])
        ):
            errors.append("BENCHMARK_STRING_NUMERIC_NOT_REJECTED")

        missing_den = _benchmark_rows()
        for row in missing_den:
            row["worker_runs"] = 0
            row["research_items"] = 0
        missing_summary = summarize_benchmark(missing_den)
        if missing_summary.get("M1_unique_relevant_evidence_per_worker_run") is not None:
            errors.append("MISSING_DENOMINATOR_CONVERTED_TO_NUMERIC_SCORE")
    except Exception as exc:
        errors.append(f"SHADOW_BENCHMARK_SMOKE_FAIL:{exc}")

    out = {
        "validator": "RESEARCH_OS_V1_RUNTIME",
        "runtime_files_checked": len(RUNTIME_FILES),
        "errors": sorted(set(errors)),
        "status": "PASS" if not errors else "FAIL_CLOSED",
        "runtime_mutation": False,
        "network_calls": False,
        "economic_conclusion": "NO_PROVEN_EDGE",
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
