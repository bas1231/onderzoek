# Research OS V1 — coordination marker

Status: **IN PROGRESS / SHADOW VALIDATION ONLY / DO NOT MERGE YET**

Owner lane: Research OS V1 architecture consolidation

Design branch: `ai/research-os-v1-prebuild-spec`

Primary integration branch: `ai/research-os-v1-integration-shadow`

Primary draft PR: **#21**

Canonical active runtime remains: `main`

## Current coordination state — 2026-09-22

Research OS V1 is being hardened as an **additive sidecar**. Other sessions may continue normal Weather, Recon, bridge, executor and hourly work on `main`.

At the latest comparison, `main` had advanced **71 commits beyond the current Research OS merge-base** while the Research OS diff remained confined to Research-OS-specific sidecar/docs/tests/benchmarks. Because several sessions are actively writing to `main`, the Research OS branch will **not be continuously rebased after every external commit**. Continuous rebasing would create unnecessary merge churn and conflict risk.

### Current merge decision

**NO MERGE NOW.** PR #21 remains draft/shadow-only.

The intended integration sequence is:

1. finish static/adversarial hardening on the Research OS sidecar;
2. freeze Research OS changes for validation;
3. perform **one final reconciliation** against the then-current `main`;
4. preserve the newest tested `main` behavior by default;
5. run Research OS tests + validators + the full current runtime regression suite locally/free;
6. run the read-only shadow planner on real current candidates/agent packets;
7. collect the preregistered unseen shadow benchmark;
8. only if the scientific replacement gate passes, review the smallest possible active-factory hook;
9. merge/activation remains a separate deliberate step — never an automatic consequence of a benchmark PASS.

If another session believes an earlier merge/rebase is required, it should record the reason in Git before changing Research OS integration semantics.

## Current hardening work

Recent Research OS audit work is targeting silent false positives, state loss and benchmark gaming. Current/just-added safeguards include:

- worker task contracts are explicit and fail closed; no scheduler-generated implicit safe action;
- unknown/non-ready legacy task states cannot silently become READY;
- duplicate/conflicting candidate IDs, task IDs, Evidence Graph nodes/edges fail closed;
- canonical candidate projection preserves conservative state and is type-strict;
- Independent Reproducer requires explicit upstream lineage before independence can PASS;
- no-signal promotion requires explicit `signal_edge=NOT_APPLICABLE`;
- **holdout is a mandatory promotion gate**; it may not be skipped;
- resurrection inherits no old PASS gates;
- shadow benchmark missing denominators remain UNKNOWN, never favorable zero;
- baseline/challenger must use identical unique preregistered case IDs;
- same case ID must preserve the same frozen case identity (ground-truth class / task shape / ACTIVE-HOUR identity) to prevent post-hoc relabeling;
- benchmark records are moving toward strict typed validation rather than permissive numeric coercion;
- temporary Plus task-slot observations are snapshots, not permanent scientific invariants.

These benchmark and promotion hardenings are being made **before the first unseen Research OS shadow dataset is accepted**.

## Implemented V1 sidecar

The sidecar includes:

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
- preregistered shadow benchmark;
- offline prebuild/runtime validators;
- architecture/historical/concurrency benchmark fixtures.

## Purpose

This file is the cross-session coordination point for Research OS V1. Other active sessions working on `main` should read it before making changes to orchestration, agent roles, candidate state, evidence/provenance, Recon promotion, scheduling or AI transport.

The redesign consolidates the current agent layer into six responsibility domains while preserving specialist checks as capabilities/gates:

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

1. **Do not merge PR #21 into `main` yet.**
2. Continue normal Weather, Recon, bridge, executor and hourly work on `main`.
3. Before changing orchestration/candidate/evidence/scheduler semantics, re-read this marker and current `main`.
4. Treat changes to `control/hourly/*`, AI transport, bridge, candidate schemas, provenance or gate behavior as Research OS integration inputs.
5. Prefer additive, backward-compatible runtime changes on `main`.
6. Do not create a competing `control/research_os_v1/*` implementation on `main` while this marker is active.
7. Preserve `NO_PROVEN_EDGE`, point-in-time, provenance, negative evidence, holdout, no-post-hoc-relaxation and execution-realistic gates.
8. Do not introduce paid API/model calls, live trading, wallet/fund movement or hidden cost paths.
9. During final reconciliation, preserve newest tested `main` behavior; never replace it with older sidecar copies.
10. New architectural failure modes should be added/proposed for Failure Memory rather than silently bypassed.
11. Do not continuously rebase PR #21 merely because unrelated sessions move `main`; reconcile once at the explicit validation freeze point unless there is a semantic overlap that requires earlier action.

## Cross-session conflict protocol

If a `main` change overlaps Research OS semantics:

1. identify the exact overlapping behavior/path;
2. prefer newest tested `main` behavior;
3. port Research OS invariants around it rather than reverting it;
4. record unresolved semantic conflict in Git;
5. fail closed rather than guessing which interpretation wins;
6. keep PR #21 draft until conflict and validation are resolved.

## Remaining validation sequence

1. finish current static/adversarial hardening;
2. freeze sidecar changes;
3. reconcile once against latest `main`;
4. run `pytest -q tests/research_os_v1` locally/free;
5. run `python -m control.research_os_v1.validate_prebuild_spec`;
6. run `python -m control.research_os_v1.validate_runtime`;
7. run full current regression tests, including hourly/bridge/Recon/Weather;
8. run `shadow_cli` on real current agent packets and candidates without runtime feedback;
9. collect at least 20 unseen candidate-events across at least 10 ACTIVE-HOUR cycles on the exact same preregistered baseline/challenger cases;
10. require holdout/reproduction/provenance/execution gates to remain non-bypassable;
11. only after the scientific replacement gate passes, review a minimal active-factory hook separately.

No automatic activation is authorized by this coordination file.

Economic default remains: `NO_PROVEN_EDGE`.
