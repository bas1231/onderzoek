from __future__ import annotations

import json
import py_compile
from pathlib import Path

from .candidate_view import canonicalize
from .contracts import validate_result_for_task, validate_task
from .discovery_coverage import summarize as summarize_coverage
from .evidence_graph import EvidenceGraph
from .failure_memory import pattern_index
from .governor import classify
from .hypothesis_accounting import adaptive_search_flags, normalize as normalize_search_family
from .legacy_adapter import packet_to_task
from .promotion import evaluate as evaluate_promotion
from .red_team import build_blind_packet
from .reproducer import source_independence
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
    "validate_schema_alignment.py",
]


def _task(task_id: str = "SMOKE", domain: str = "market_research") -> dict:
    return {
        "task_id": task_id,
        "candidate_id": "C1",
        "worker_domain": domain,
        "objective": "runtime smoke test",
        "state": "READY",
        "task_shape": {
            "parallelism": "LOW",
            "dependency_shape": "SEQUENTIAL",
            "uncertainty_type": "MARKET",
            "time_sensitivity": "LOW",
            "novelty": "INCREMENTAL",
            "decision_relevance": "HIGH",
        },
        "inputs": {},
        "constraints": {
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
            "source_policy": "LOCAL_EXISTING_ONLY",
        },
        "expected_output": {
            "artifact_type": "RESEARCH_FINDING",
            "required_fields": ["evidence"],
        },
        "scheduling": {
            "uncertainty_reduction": "HIGH",
            "dependency_unlock_value": "ONE",
            "evidence_cost": "LOW",
            "model_cost": "MEDIUM",
            "duplication_risk": "LOW",
        },
        "proposed_action": {
            "kind": "free_public_read_only_research",
            "provenance": True,
            "point_in_time": True,
        },
    }


def _result(domain: str = "market_research", economic: str = "NO_PROVEN_EDGE") -> dict:
    return {
        "task_id": "SMOKE",
        "candidate_id": "C1",
        "worker_domain": domain,
        "status": "COMPLETE",
        "claims": [],
        "evidence": [],
        "contradictions": [],
        "unknowns": [],
        "gate_effect": [],
        "economic_conclusion": economic,
    }


def _all_pass_gates() -> dict[str, str]:
    return {
        gate: "PASS"
        for gate in [
            "source_provenance",
            "point_in_time",
            "mechanism",
            "signal_edge",
            "market_edge",
            "execution_reality",
            "prebuild_killer",
            "chief_falsifier",
            "validation",
            "holdout",
            "independent_reproduction",
            "shadow",
        ]
    }


def _benchmark_rows(*, better: bool = False, prefix: str = "CASE") -> list[dict]:
    rows: list[dict] = []
    for i in range(20):
        ground_truth = "SURVIVOR" if i == 0 else "DECISIVE_NEGATIVE"
        rows.append({
            "case_id": f"{prefix}-{i:02d}",
            "active_hour_id": f"H{i // 2}",
            "task_shape": "PARALLEL" if i % 2 else "SEQUENTIAL",
            "ground_truth_class": ground_truth,
            "decision": "KEEP" if ground_truth == "SURVIVOR" else "KILL",
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
            "source_families_covered": ["official", "code"],
            "hard_failures": [],
        })
    return rows


def _expect_raises(errors: list[str], label: str, fn, contains: str) -> None:
    try:
        fn()
        errors.append(f"{label}:NO_EXCEPTION")
    except ValueError as exc:
        if contains not in str(exc):
            errors.append(f"{label}:WRONG_EXCEPTION:{exc}")


def main() -> int:
    errors: list[str] = []

    # Syntax/import surface.
    for name in RUNTIME_FILES:
        path = BASE / name
        if not path.is_file():
            errors.append(f"MISSING_RUNTIME_FILE:{name}")
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:
            errors.append(f"COMPILE_FAIL:{name}:{exc}")

    # Failure Memory and Governor remain hard fail-closed boundaries.
    try:
        if len(pattern_index()) < 30:
            errors.append("FAILURE_MEMORY_TOO_SMALL")
        if classify({"kind": "magic_unknown_action"}).admissible:
            errors.append("GOVERNOR_UNKNOWN_ACTION_ALLOWED")
        for kind in ("paid_action", "live_order_or_trade", "wallet_or_fund_movement"):
            if not classify({"kind": kind}).requires_user_approval:
                errors.append(f"GOVERNOR_APPROVAL_GATE_MISSING:{kind}")
    except Exception as exc:
        errors.append(f"GOVERNOR_OR_MEMORY_SMOKE_FAIL:{exc}")

    # Canonical candidate projection must preserve negatives and reject ambiguity.
    try:
        base = canonicalize(
            {"candidate_id": "C1", "hypothesis": "h", "gates": {}},
            source_commit="smoke",
        )
        if base["economic_status"] != "NO_PROVEN_EDGE":
            errors.append("CANDIDATE_DEFAULT_NOT_NO_PROVEN_EDGE")
        partial = canonicalize(
            {
                "candidate_id": "C2",
                "hypothesis": "h",
                "gates": {"prebuild_killer": "PASS_DISCOVERY_ONLY"},
            },
            source_commit="smoke",
        )
        if partial["required_gates"]["prebuild_killer"] != "PENDING":
            errors.append("PARTIAL_LEGACY_GATE_UPGRADED_TO_PASS")
        _expect_raises(
            errors,
            "UNKNOWN_QUEUE_STATUS_ACCEPTED",
            lambda: canonicalize(
                {"candidate_id": "C3", "hypothesis": "h", "queue_status": "MYSTERY"},
                source_commit="smoke",
            ),
            "unknown_queue_status",
        )
        _expect_raises(
            errors,
            "CONFLICTING_GATE_STATE_ACCEPTED",
            lambda: canonicalize(
                {
                    "candidate_id": "C4",
                    "hypothesis": "h",
                    "gates": {"mechanism": "FAIL"},
                    "required_gates": {"mechanism": "PASS"},
                },
                source_commit="smoke",
            ),
            "conflicting_gate_state",
        )
    except Exception as exc:
        errors.append(f"CANDIDATE_SMOKE_FAIL:{exc}")

    # Scheduler contracts and identity.
    try:
        valid = _task()
        if validate_task(valid):
            errors.append("VALID_TASK_REJECTED")
        if fanout_cap(valid) != 1:
            errors.append("SEQUENTIAL_FANOUT_NOT_ONE")
        if schedule([valid])["selected"] != ["SMOKE"]:
            errors.append("VALID_TASK_NOT_SCHEDULED")
        _expect_raises(
            errors,
            "DUPLICATE_TASK_ID_ACCEPTED",
            lambda: schedule([valid, dict(valid)]),
            "duplicate_task_id",
        )
        unknown_legacy = packet_to_task(
            {"agent_id": "settlement", "status": "MYSTERY_STATE", "input_refs": ["x"]},
            "SMOKE-RUN",
        )
        if unknown_legacy is None or unknown_legacy.get("state") != "BLOCKED":
            errors.append("UNKNOWN_LEGACY_STATUS_NOT_BLOCKED")
    except Exception as exc:
        errors.append(f"SCHEDULER_SMOKE_FAIL:{exc}")

    # Evidence Graph requires provenance, point-in-time status and coherent polarity.
    try:
        evidence = {
            "id": "e1",
            "type": "evidence",
            "status": "OK",
            "created_at": "2026-09-21T00:00:00Z",
            "producer": "smoke",
            "source_ref": "raw/e1.json",
            "point_in_time_status": "UNKNOWN",
        }
        claim = {
            "id": "c1",
            "type": "claim",
            "status": "OPEN",
            "created_at": "2026-09-21T00:00:00Z",
            "producer": "smoke",
        }
        graph = EvidenceGraph({"schema_version": 1, "nodes": [evidence, claim], "edges": []})
        graph.add_edge({
            "from": "e1", "to": "c1", "type": "supports",
            "created_at": "2026-09-21T00:00:00Z", "producer": "smoke",
        })
        _expect_raises(
            errors,
            "CONFLICTING_GRAPH_POLARITY_ACCEPTED",
            lambda: graph.add_edge({
                "from": "e1", "to": "c1", "type": "contradicts",
                "created_at": "2026-09-21T00:00:01Z", "producer": "smoke",
            }),
            "conflicting_edge_polarity",
        )
        bad_evidence = dict(evidence)
        bad_evidence.pop("source_ref")
        _expect_raises(
            errors,
            "EVIDENCE_WITHOUT_PROVENANCE_ACCEPTED",
            lambda: EvidenceGraph({"schema_version": 1, "nodes": [bad_evidence], "edges": []}),
            "evidence_provenance_required",
        )
    except Exception as exc:
        errors.append(f"EVIDENCE_GRAPH_SMOKE_FAIL:{exc}")

    # Search-family accounting may never turn missing search history into a clean trial.
    try:
        zero_trial = adaptive_search_flags({
            "id": "F0",
            "hypotheses_examined": 0,
            "parameterizations_examined": 0,
            "post_hoc_mutations": 0,
            "untouched_evidence_remaining": True,
        })
        if zero_trial.get("promotion_blocker") != "NO_SEARCH_TRIAL_RECORDED":
            errors.append("ZERO_TRIAL_ACCOUNTING_NOT_BLOCKED")
        _expect_raises(
            errors,
            "RESOLVED_VARIANTS_EXCEED_SEARCH_SPACE",
            lambda: normalize_search_family({
                "id": "BAD",
                "hypotheses_examined": 1,
                "parameterizations_examined": 0,
                "post_hoc_mutations": 0,
                "failed_variants": 1,
                "surviving_variants": 1,
                "untouched_evidence_remaining": True,
            }),
            "resolved_variants_exceed_recorded_search_space",
        )
    except Exception as exc:
        errors.append(f"HYPOTHESIS_ACCOUNTING_SMOKE_FAIL:{exc}")

    # Coverage requires explicit retrieval success and deduplicates mirrored documents.
    try:
        unknown = summarize_coverage(
            [{"source_id": "a", "source_family": "OFFICIAL"}],
            [],
            ["official"],
            ["official"],
        )
        if unknown.get("coverage_retrieval_complete") is not False:
            errors.append("MISSING_RETRIEVAL_STATUS_COUNTED_AS_SUCCESS")
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

    # Promotion requires all known + future required gates and never authorizes live action.
    try:
        gates = _all_pass_gates()
        promoted = evaluate_promotion({"required_gates": gates})
        if promoted.get("status") != "PROMOTION_CANDIDATE":
            errors.append("FULL_GATE_SET_NOT_PROMOTION_CANDIDATE")
        if promoted.get("live_trading_authorized") is not False:
            errors.append("PROMOTION_AUTHORIZED_LIVE_TRADING")
        future = dict(gates)
        future["future_integrity_gate"] = "FAIL"
        if evaluate_promotion({"required_gates": future}).get("eligible") is not False:
            errors.append("FUTURE_FAILED_GATE_IGNORED")
        missing_holdout = dict(gates)
        missing_holdout.pop("holdout")
        if evaluate_promotion({"required_gates": missing_holdout}).get("eligible") is not False:
            errors.append("HOLDOUT_NOT_REQUIRED")
    except Exception as exc:
        errors.append(f"PROMOTION_SMOKE_FAIL:{exc}")

    # Blind Red Team receives no prior gate verdicts.
    try:
        blind = build_blind_packet({
            "candidate_id": "C1",
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
    except Exception as exc:
        errors.append(f"RED_TEAM_SMOKE_FAIL:{exc}")

    # Reproduction must be truly source-independent, not merely differently named.
    try:
        same_hash = source_independence(
            [{"ref": "a", "document_sha256": "ABC", "upstream_source_ids": ["claimed:a"]}],
            [{"ref": "b", "content_hash": "abc", "upstream_source_ids": ["claimed:b"]}],
        )
        if same_hash.get("counts_as_independent_reproduction") is not False:
            errors.append("SAME_CONTENT_HASH_COUNTED_AS_INDEPENDENT")
        disjoint = source_independence(
            [{"ref": "a", "document_sha256": "aaa", "upstream_source_ids": ["source:a"]}],
            [{"ref": "b", "document_sha256": "bbb", "upstream_source_ids": ["source:b"]}],
        )
        if disjoint.get("counts_as_independent_reproduction") is not True:
            errors.append("DISJOINT_EXPLICIT_LINEAGE_NOT_RECOGNIZED")
    except Exception as exc:
        errors.append(f"REPRODUCTION_SMOKE_FAIL:{exc}")

    # Result authority binds worker conclusions and gate changes to actual evidence.
    try:
        discovery_task = _task(domain="discovery")
        discovery_result = _result(domain="discovery", economic="RESEARCH_POSITIVE")
        if "discovery_may_not_emit_positive_economic_conclusion" not in validate_result_for_task(discovery_task, discovery_result):
            errors.append("DISCOVERY_POSITIVE_RESULT_NOT_BLOCKED")

        research_task = _task()
        invented_basis = _result()
        invented_basis["evidence"] = [{
            "source_ref": "raw/real.json",
            "point_in_time_status": "PASS",
        }]
        invented_basis["gate_effect"] = [{
            "gate": "mechanism",
            "state": "PASS",
            "basis_refs": ["raw/invented.json"],
        }]
        if not any(
            error.startswith("gate_effect_unknown_basis_ref")
            for error in validate_result_for_task(research_task, invented_basis)
        ):
            errors.append("INVENTED_GATE_BASIS_NOT_BLOCKED")
    except Exception as exc:
        errors.append(f"RESULT_AUTHORITY_SMOKE_FAIL:{exc}")

    # Resurrection preserves history but inherits no old validation pass.
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
    except Exception as exc:
        errors.append(f"RESURRECTION_SMOKE_FAIL:{exc}")

    # Benchmark replacement is matched-case, frozen-metadata and denominator safe.
    try:
        baseline = summarize_benchmark(_benchmark_rows())
        challenger = summarize_benchmark(_benchmark_rows(better=True))
        verdict = replacement_check(baseline, challenger)
        if verdict.get("scientific_replacement_gate_met") is not True:
            errors.append("MATCHED_BENCHMARK_REPLACEMENT_CHECK_FAILED")

        relabelled_rows = _benchmark_rows(better=True)
        relabelled_rows[1]["ground_truth_class"] = "SURVIVOR"
        relabelled = summarize_benchmark(relabelled_rows)
        relabelled_verdict = replacement_check(baseline, relabelled)
        if relabelled_verdict.get("scientific_replacement_gate_met") is not False:
            errors.append("RELABELLED_CASE_ALLOWED_REPLACEMENT")

        missing_den = _benchmark_rows()
        for row in missing_den:
            row["worker_runs"] = 0
            row["research_items"] = 0
        missing_summary = summarize_benchmark(missing_den)
        if missing_summary.get("M1_unique_relevant_evidence_per_worker_run") is not None:
            errors.append("MISSING_DENOMINATOR_CONVERTED_TO_SCORE")
    except Exception as exc:
        errors.append(f"SHADOW_BENCHMARK_SMOKE_FAIL:{exc}")

    out = {
        "validator": "RESEARCH_OS_V1_RUNTIME_V2",
        "runtime_files_checked": len(RUNTIME_FILES),
        "errors": sorted(set(errors)),
        "status": "PASS" if not errors else "FAIL_CLOSED",
        "runtime_mutation": False,
        "network_calls": False,
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "economic_conclusion": "NO_PROVEN_EDGE",
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
