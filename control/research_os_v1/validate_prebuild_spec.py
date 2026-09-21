#!/usr/bin/env python3
"""Offline, read-only validator for the Research OS V1 pre-build specification.

This validator changes no runtime state and performs no network calls.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "control" / "research_os_v1"
BENCH = ROOT / "benchmarks" / "research_os_v1"
DOCS = ROOT / "docs"

JSON_FILES = [
    BASE / "governor_policy.json",
    BASE / "scheduler_policy.json",
    BASE / "task_shape_policy.json",
    BASE / "discovery_coverage_policy.json",
    BASE / "model_budget_policy.json",
    BASE / "worker_contract.schema.json",
    BASE / "evidence_graph.schema.json",
    BASE / "canonical_candidate.schema.json",
    BASE / "failure_patterns.json",
    BASE / "role_migration.json",
    BENCH / "historical_replay.json",
    BENCH / "architecture_red_team.json",
    BENCH / "concurrency_experiment.json",
    BENCH / "shadow_acceptance.json",
]
DOC_FILES = [
    DOCS / "RESEARCH_OS_V1_PREBUILD_SPEC.md",
    DOCS / "RESEARCH_OS_V1_PREBUILD_AUDIT.md",
    DOCS / "RESEARCH_OS_V1_WORKER_CONTRACTS.md",
    DOCS / "RESEARCH_OS_V1_ROLLOUT_PLAN.md",
    DOCS / "RESEARCH_OS_V1_DECISION_LOG.md",
    DOCS / "PLUS_NATIVE_RESEARCH_OS_CANARY.md",
]


def fail(errors: list[str], msg: str) -> None:
    errors.append(msg)


def load_json(path: Path, errors: list[str]):
    if not path.is_file():
        fail(errors, f"MISSING_FILE:{path.relative_to(ROOT)}")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(errors, f"INVALID_JSON:{path.relative_to(ROOT)}:{exc}")
        return None


def main() -> int:
    errors: list[str] = []
    objs = {p.name: load_json(p, errors) for p in JSON_FILES}
    for p in DOC_FILES:
        if not p.is_file():
            fail(errors, f"MISSING_FILE:{p.relative_to(ROOT)}")

    patterns_obj = objs.get("failure_patterns.json") or {}
    patterns = patterns_obj.get("patterns") or []
    fp_ids = [str(x.get("id")) for x in patterns if isinstance(x, dict)]
    if len(fp_ids) != len(set(fp_ids)):
        fail(errors, "DUPLICATE_FAILURE_PATTERN_ID")
    fp_set = set(fp_ids)

    for bench_name in ["historical_replay.json", "architecture_red_team.json"]:
        bench = objs.get(bench_name) or {}
        rows = bench.get("cases") if bench_name == "historical_replay.json" else bench.get("scenarios")
        for row in rows or []:
            for fp in row.get("failure_patterns", row.get("patterns", [])) or []:
                if fp not in fp_set:
                    fail(errors, f"UNKNOWN_FAILURE_PATTERN:{bench_name}:{row.get('id')}:{fp}")

    migration = objs.get("role_migration.json") or {}
    valid_domains = {
        "discovery", "market_research", "mechanics", "algebra",
        "red_team", "research_director", "independent_reproducer"
    }
    legacy = migration.get("legacy_to_domain") or {}
    expected_legacy = {
        "recon_scout", "scout", "weather_twc", "microstructure", "behavioral",
        "informed_flow", "algebra", "settlement", "prebuild_killer",
        "chief_falsifier", "independent_reproducer", "research_director"
    }
    if set(legacy) != expected_legacy:
        fail(errors, f"LEGACY_ROLE_MAPPING_MISMATCH:{sorted(set(legacy) ^ expected_legacy)}")
    for old, item in legacy.items():
        if item.get("domain") not in valid_domains:
            fail(errors, f"UNKNOWN_MIGRATION_DOMAIN:{old}:{item.get('domain')}")

    governor = objs.get("governor_policy.json") or {}
    gov_rules = {r.get("match"): r.get("decision") for r in governor.get("rules", [])}
    required_governor = {
        "paid_action": "BLOCK_USER_APPROVAL",
        "live_order_or_trade": "BLOCK_USER_APPROVAL",
        "wallet_or_fund_movement": "BLOCK_USER_APPROVAL",
        "credential_mutation_or_secret_export": "BLOCK",
        "post_close_or_later_revision_backfill_into_point_in_time_decision": "BLOCK",
        "relax_failed_gate_post_hoc": "BLOCK",
    }
    for match, decision in required_governor.items():
        if gov_rules.get(match) != decision:
            fail(errors, f"GOVERNOR_INVARIANT_MISSING:{match}:{decision}")

    scheduler = objs.get("scheduler_policy.json") or {}
    if scheduler.get("reproducibility", {}).get("policy_frozen_during_shadow_benchmark") is not True:
        fail(errors, "SCHEDULER_NOT_FROZEN_FOR_SHADOW")
    if scheduler.get("protected_capacity", {}).get("discovery_required_each_active_hour") is not True:
        fail(errors, "DISCOVERY_NOT_PROTECTED")

    shape = objs.get("task_shape_policy.json") or {}
    fanout = shape.get("fanout") or {}
    if fanout.get("LOW_SEQUENTIAL", {}).get("max_specialist_workers") != 1:
        fail(errors, "SEQUENTIAL_FANOUT_NOT_CAPPED_AT_ONE")
    if "HIGH_INDEPENDENT" not in fanout:
        fail(errors, "HIGH_INDEPENDENT_FANOUT_POLICY_MISSING")

    coverage = objs.get("discovery_coverage_policy.json") or {}
    if len(coverage.get("source_families") or []) < 8:
        fail(errors, "DISCOVERY_SOURCE_FAMILIES_TOO_NARROW")
    if coverage.get("coverage_debt", {}).get("track_across_active_hours") is not True:
        fail(errors, "DISCOVERY_COVERAGE_DEBT_DISABLED")

    budget = objs.get("model_budget_policy.json") or {}
    no_spend = budget.get("no_hidden_spend") or {}
    for key in ["automatic_credit_purchase", "openai_api_key_fallback", "paid_external_model_fallback"]:
        if no_spend.get(key) is not False:
            fail(errors, f"MODEL_BUDGET_HIDDEN_SPEND_NOT_DISABLED:{key}")
    if len(budget.get("capability_tiers") or {}) < 4:
        fail(errors, "MODEL_CAPABILITY_TIERS_INCOMPLETE")

    shadow = objs.get("shadow_acceptance.json") or {}
    hard = "\n".join(shadow.get("hard_fail_conditions") or []).lower()
    for word in ["paid", "live", "wallet", "point-in-time", "failed required gate"]:
        if word not in hard:
            fail(errors, f"SHADOW_HARD_FAIL_MISSING:{word}")

    worker_schema = objs.get("worker_contract.schema.json") or {}
    worker_constraints = (
        worker_schema.get("properties", {})
        .get("constraints", {})
        .get("properties", {})
    )
    for key in ["live_trading", "paid_actions", "wallet_actions"]:
        if worker_constraints.get(key, {}).get("const") is not False:
            fail(errors, f"WORKER_CONSTRAINT_NOT_FALSE:{key}")

    replay = objs.get("historical_replay.json") or {}
    replay_ids = [c.get("id") for c in replay.get("cases", [])]
    if len(replay_ids) < 20:
        fail(errors, f"HISTORICAL_REPLAY_TOO_SMALL:{len(replay_ids)}")
    if len(replay_ids) != len(set(replay_ids)):
        fail(errors, "DUPLICATE_HISTORICAL_REPLAY_ID")
    if not any(c.get("premature_kill_risk") == "HIGH" for c in replay.get("cases", [])):
        fail(errors, "REPLAY_HAS_NO_SURVIVOR_ANTI_OVERKILL_CASE")

    art = objs.get("architecture_red_team.json") or {}
    art_ids = [c.get("id") for c in art.get("scenarios", [])]
    if len(art_ids) < 30:
        fail(errors, f"ARCH_RED_TEAM_TOO_SMALL:{len(art_ids)}")
    if len(art_ids) != len(set(art_ids)):
        fail(errors, "DUPLICATE_ARCH_RED_TEAM_ID")

    output = {
        "validator": "RESEARCH_OS_V1_PREBUILD",
        "json_files_checked": len(JSON_FILES),
        "doc_files_checked": len(DOC_FILES),
        "failure_patterns": len(fp_ids),
        "historical_cases": len(replay_ids),
        "architecture_scenarios": len(art_ids),
        "errors": errors,
        "status": "PASS" if not errors else "FAIL_CLOSED",
        "economic_conclusion": "NO_PROVEN_EDGE",
        "network_calls": False,
        "runtime_mutation": False,
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
