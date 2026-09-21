from __future__ import annotations

import json
import py_compile
from pathlib import Path

from .candidate_view import canonicalize
from .failure_memory import pattern_index
from .governor import classify
from .scheduler import fanout_cap
from .hypothesis_accounting import adaptive_search_flags
from .promotion import evaluate as evaluate_promotion
from .reproducer import source_independence
from .resurrection import evaluate as evaluate_resurrection
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
            {
                "candidate_id": "SMOKE",
                "hypothesis": "h",
                "decision": "UNPROVEN",
                "gates": {},
            },
            source_commit="smoke",
        )
        if candidate["economic_status"] != "NO_PROVEN_EDGE":
            errors.append("CANDIDATE_DEFAULT_NOT_NO_PROVEN_EDGE")

        canonical = canonicalize(
            {
                "candidate_id": "SMOKE-CANON",
                "hypothesis": "h",
                "required_gates": {
                    "mechanism": "PASS",
                    "execution_reality": "FAIL",
                },
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
        task = {
            "task_shape": {
                "parallelism": "LOW",
                "dependency_shape": "SEQUENTIAL",
            }
        }
        if fanout_cap(task) != 1:
            errors.append("SEQUENTIAL_FANOUT_NOT_ONE")
    except Exception as exc:
        errors.append(f"SCHEDULER_SMOKE_FAIL:{exc}")

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
    except Exception as exc:
        errors.append(f"HYPOTHESIS_ACCOUNTING_SMOKE_FAIL:{exc}")

    try:
        gates = {
            g: "PASS"
            for g in [
                "source_provenance",
                "point_in_time",
                "mechanism",
                "signal_edge",
                "market_edge",
                "execution_reality",
                "prebuild_killer",
                "chief_falsifier",
                "validation",
                "independent_reproduction",
                "shadow",
            ]
        }
        verdict = evaluate_promotion({"required_gates": gates})
        if verdict.get("live_trading_authorized") is not False:
            errors.append("PROMOTION_AUTHORIZED_LIVE_TRADING")

        gates["signal_edge"] = "PENDING"
        no_signal = evaluate_promotion(
            {"required_gates": gates},
            signal_required=False,
        )
        if no_signal.get("eligible") is not False:
            errors.append("NO_SIGNAL_ROUTE_SKIPPED_UNRESOLVED_SIGNAL_GATE")
    except Exception as exc:
        errors.append(f"PROMOTION_SMOKE_FAIL:{exc}")

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
    except Exception as exc:
        errors.append(f"REPRODUCTION_SMOKE_FAIL:{exc}")

    try:
        resurrected = evaluate_resurrection(
            {
                "candidate_id": "R",
                "queue_status": "CLOSED_NEGATIVE",
                "economic_status": "TESTED_NEGATIVE",
                "resurrection_conditions": ["regime_change"],
                "required_gates": {
                    "source_provenance": "PASS",
                    "mechanism": "PASS",
                },
            },
            ["regime_change"],
            "2026-09-21T00:00:00Z",
        )
        if resurrected["candidate"]["required_gates"].get("source_provenance") != "PENDING":
            errors.append("RESURRECTION_INHERITED_OLD_PROVENANCE_PASS")
    except Exception as exc:
        errors.append(f"RESURRECTION_SMOKE_FAIL:{exc}")

    try:
        baseline = summarize_benchmark(_benchmark_rows())
        challenger = summarize_benchmark(_benchmark_rows(better=True))
        replacement = replacement_check(baseline, challenger)
        if replacement.get("scientific_replacement_gate_met") is not True:
            errors.append("MATCHED_BENCHMARK_REPLACEMENT_CHECK_FAILED")

        mismatched = summarize_benchmark(
            _benchmark_rows(better=True, case_prefix="OTHER")
        )
        mismatch_verdict = replacement_check(baseline, mismatched)
        if mismatch_verdict.get("scientific_replacement_gate_met") is not False:
            errors.append("MISMATCHED_CASE_SET_ALLOWED_REPLACEMENT")

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
        "errors": errors,
        "status": "PASS" if not errors else "FAIL_CLOSED",
        "runtime_mutation": False,
        "network_calls": False,
        "economic_conclusion": "NO_PROVEN_EDGE",
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
