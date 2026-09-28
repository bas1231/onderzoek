# Research OS V1 — Design Index

Status: **PRE-BUILD / SHADOW SPECIFICATION ONLY**

Branch: `ai/research-os-v1-prebuild-spec`

This branch intentionally does not modify the active factory on `main`.

## Core architecture

- `docs/RESEARCH_OS_V1_PREBUILD_SPEC.md` — frozen V1 architecture and non-goals.
- `docs/RESEARCH_OS_V1_PREBUILD_AUDIT.md` — findings, blockers and go/no-go state.
- `docs/RESEARCH_OS_V1_WORKER_CONTRACTS.md` — exact context/output responsibilities.
- `docs/RESEARCH_OS_V1_ROLLOUT_PLAN.md` — staged no-regression migration.
- `docs/RESEARCH_OS_V1_DECISION_LOG.md` — rejected alternatives and reconsideration rules.
- `docs/PLUS_NATIVE_RESEARCH_OS_CANARY.md` — Plus-native task/app transport canary.

## Control-plane specifications

- `control/research_os_v1/governor_policy.json`
- `control/research_os_v1/scheduler_policy.json`
- `control/research_os_v1/task_shape_policy.json`
- `control/research_os_v1/discovery_coverage_policy.json`
- `control/research_os_v1/model_budget_policy.json`
- `control/research_os_v1/account_aware_plus_topology.json`
- `control/research_os_v1/role_migration.json`
- `control/research_os_v1/failure_patterns.json`
- `control/research_os_v1/worker_contract.schema.json`
- `control/research_os_v1/canonical_candidate.schema.json`
- `control/research_os_v1/evidence_graph.schema.json`
- `control/research_os_v1/validate_prebuild_spec.py`

## Benchmarks

- `benchmarks/research_os_v1/historical_replay.json` — mixed counterfactual coverage suite, including anti-overkill survivors.
- `benchmarks/research_os_v1/architecture_red_team.json` — architecture failure scenarios.
- `benchmarks/research_os_v1/concurrency_experiment.json` — preregistered 1–6 worker scaling test.
- `benchmarks/research_os_v1/shadow_acceptance.json` — frozen challenger-vs-baseline acceptance criteria.

## Current Plus account constraint captured by the design

At audit time all five active Scheduled Task slots are occupied: four prediction-research report slots plus one existing non-prediction task. Research OS therefore assumes only four prediction-task slots unless the user explicitly changes the existing non-prediction task. The account-aware topology maps those four research slots to:

1. Primary Scout
2. Recon Scout
3. Dynamic Specialist / Red Team / temporary Reproducer
4. Research Director

This is a target topology, not an activated schedule. The current task configuration has not been changed.

## Mandatory order before runtime changes

1. Reconcile this design snapshot against the then-current `main`.
2. Run the offline pre-build validator locally.
3. Build a read-only canonical-candidate adapter.
4. Run Failure Memory and scheduler in shadow only.
5. Pass unseen shadow acceptance criteria.
6. Canary native Plus/GitHub task behavior before relying on it.
7. Cut over incrementally with rollback, never via blind branch overwrite.

Economic default remains `NO_PROVEN_EDGE`.
