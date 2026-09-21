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
            {"candidate_id": "SMOKE", "hypothesis": "h", "decision": "UNPROVEN", "gates": {}},
            source_commit="smoke",
        )
        if candidate["economic_status"] != "NO_PROVEN_EDGE":
            errors.append("CANDIDATE_DEFAULT_NOT_NO_PROVEN_EDGE")
    except Exception as exc:
        errors.append(f"CANDIDATE_SMOKE_FAIL:{exc}")

    try:
        task = {"task_shape": {"parallelism": "LOW", "dependency_shape": "SEQUENTIAL"}}
        if fanout_cap(task) != 1:
            errors.append("SEQUENTIAL_FANOUT_NOT_ONE")
    except Exception as exc:
        errors.append(f"SCHEDULER_SMOKE_FAIL:{exc}")

    try:
        flags = adaptive_search_flags({
            "id": "SMOKE", "hypotheses_examined": 2, "parameterizations_examined": 0,
            "post_hoc_mutations": 0, "untouched_evidence_remaining": True,
        })
        if flags.get("discovery_evidence_may_promote_directly") is not False:
            errors.append("ADAPTIVE_SEARCH_NOT_DOWNGRADED")
    except Exception as exc:
        errors.append(f"HYPOTHESIS_ACCOUNTING_SMOKE_FAIL:{exc}")

    try:
        gates = {g: "PASS" for g in [
            "source_provenance", "point_in_time", "mechanism", "signal_edge",
            "market_edge", "execution_reality", "prebuild_killer", "chief_falsifier",
            "validation", "independent_reproduction", "shadow",
        ]}
        verdict = evaluate_promotion({"required_gates": gates})
        if verdict.get("live_trading_authorized") is not False:
            errors.append("PROMOTION_AUTHORIZED_LIVE_TRADING")
    except Exception as exc:
        errors.append(f"PROMOTION_SMOKE_FAIL:{exc}")

    try:
        indep = source_independence(["same"], ["same"])
        if indep.get("counts_as_independent_reproduction") is not False:
            errors.append("SHARED_SOURCE_COUNTED_AS_INDEPENDENT")
    except Exception as exc:
        errors.append(f"REPRODUCTION_SMOKE_FAIL:{exc}")

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
