# Research OS V1 — coordination marker

Status: **IN PROGRESS / SHADOW VALIDATION ONLY**

Owner lane: Research OS V1 architecture consolidation

Design branch: `ai/research-os-v1-prebuild-spec`

Primary integration branch: `ai/research-os-v1-integration-shadow`

Primary draft PR: **#21**

Canonical runtime remains: `main`

## Current integration state

Research OS V1 has been reconciled on top of the V14.1 `main` line without replacing current hourly/bridge/Recon/Weather behavior. The integration branch is additive: it contributes Research-OS-specific sidecar code, tests, benchmarks and documentation only.

The sidecar now includes:

- deterministic Governor;
- canonical candidate adapter with negative-state preservation;
- reusable Failure Memory;
- idempotent Evidence Graph;
- worker contracts;
- task-shape scheduler/fanout caps;
- read-only shadow planner/CLI;
- hypothesis and multiple-testing accounting;
- Primary/Recon source-coverage accounting;
- deterministic promotion gate;
- resurrection with complete gate reset and preserved history;
- blind Red-Team packet construction;
- Independent Reproducer source-lineage checks;
- preregistered shadow benchmark with matched case IDs and fail-closed missing-denominator handling;
- offline prebuild/runtime validators;
- architecture/historical/concurrency benchmark fixtures.

Static audit hardening completed before unseen shadow data:

1. no-signal promotion requires explicit `signal_edge=NOT_APPLICABLE`;
2. independent reproduction requires explicit upstream source lineage for a positive independence decision;
3. resurrection inherits no old PASS gate;
4. re-canonicalization preserves explicit required gates and CLOSED_NEGATIVE state;
5. shadow baseline/challenger must use the same unique case IDs;
6. absent metric denominators are UNKNOWN, never favorable zero.

These benchmark-comparability changes were frozen before the first unseen Research OS shadow observation and recorded as AD-021.

Local full validation against the reconciled integration branch is still required before PR #21 may leave draft. Do not report it as passed until an actual executor/local result exists.

## Purpose

This file is the cross-session coordination point for Research OS V1. Other active sessions working on `main` should read it before making changes to orchestration, agent roles, candidate state, evidence/provenance, Recon promotion, scheduling or AI transport.

The redesign consolidates the current agent layer into six responsibility domains while preserving existing specialist checks as capabilities/gates:

1. Discovery
2. Market Research
3. Mechanics
4. Algebra
5. Red Team / Pentest
6. Research Director

Independent Reproduction remains a temporary isolated validation step rather than a permanent seventh role.

## Owned Research OS paths

- `control/research_os_v1/*`
- `benchmarks/research_os_v1/*`
- `docs/RESEARCH_OS_V1_*`
- `docs/PLUS_NATIVE_RESEARCH_OS_CANARY.md`
- `tests/research_os_v1/*`

No existing `control/hourly/*`, bridge, Recon, Weather or executor file should be replaced by the Research OS sidecar during shadow construction.

## Coordination rules for other sessions

1. **Do not merge PR #21 into `main` yet.** It remains shadow-only until local validation and the preregistered unseen benchmark pass.
2. Continue normal Weather, Recon, bridge, executor and hourly work on `main`.
3. Before changing orchestration/candidate/evidence/scheduler semantics, re-read this marker and current `main`.
4. Treat changes to `control/hourly/*`, AI transport, bridge, candidate schemas, provenance or gate behavior as Research OS integration inputs.
5. Prefer additive, backward-compatible runtime changes on `main`.
6. Do not create competing `control/research_os_v1/*` implementations on `main` while this marker is active.
7. Preserve `NO_PROVEN_EDGE`, point-in-time, provenance, negative evidence, no-post-hoc-relaxation and execution-realistic gates.
8. Do not introduce paid API/model calls, live trading, wallet/fund movement or hidden cost paths.
9. During reconciliation, preserve the newest tested `main` behavior; never replace it with older Research OS branch copies.
10. New architectural failure modes should be added/proposed for Failure Memory rather than silently bypassed.
11. Integration remains sidecar-first and shadow-only until the preregistered benchmark passes.

## Cross-session conflict protocol

When `main` advances again:

1. read the new `main` head;
2. compare overlap paths;
3. preserve newest tested `main` implementation by default;
4. port only Research OS additive subtrees/docs;
5. run existing hourly/bridge/Recon/Weather tests plus Research OS tests;
6. fail closed on semantic conflict;
7. keep PR #21 draft until shadow acceptance passes.

## Remaining validation sequence

1. run `pytest -q tests/research_os_v1` locally/free;
2. run `python -m control.research_os_v1.validate_prebuild_spec`;
3. run `python -m control.research_os_v1.validate_runtime`;
4. run full current regression tests;
5. run `shadow_cli` on real current agent packets and candidates without runtime feedback;
6. collect at least 20 unseen candidate-events across at least 10 ACTIVE-HOUR cycles on the exact same preregistered baseline/challenger case IDs;
7. only after the scientific replacement gate passes, review a minimal active-factory hook separately.

No automatic activation is authorized by this coordination file.

Economic default remains: `NO_PROVEN_EDGE`.
