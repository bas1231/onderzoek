# Research OS V1 — coordination marker

Status: **IN PROGRESS / DESIGN + SHADOW IMPLEMENTATION ONLY**

Owner lane: Research OS V1 architecture consolidation

Design branch: `ai/research-os-v1-prebuild-spec`

Runtime staging branch: `ai/research-os-v1-runtime-staging`

Canonical runtime remains: `main`

Latest `main` observed by this lane during coordination refresh: current main at time of each integration check; do not rely on an older recorded SHA.

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

## CURRENT ACTIVE BUILD ZONE

Research OS is being implemented as a **sidecar shadow runtime**. Design/specification remains on `ai/research-os-v1-prebuild-spec`; executable shadow modules are being staged on `ai/research-os-v1-runtime-staging` so the prebuild spec remains clean while runtime code is hardened.

Paths owned by this lane on the Research OS branches:

- `control/research_os_v1/*`
- `benchmarks/research_os_v1/*`
- `docs/RESEARCH_OS_V1_*`
- `docs/PLUS_NATIVE_RESEARCH_OS_CANARY.md`
- `tests/research_os_v1/*`

Current runtime staging implementation includes:

- deterministic policy loader and Governor;
- canonical candidate adapter;
- reusable Failure Memory (pattern hit -> mandatory check, never automatic kill);
- minimal idempotent Evidence Graph with conflict rejection;
- worker task/result contract validation;
- ordinal scheduler and task-shape fanout caps;
- read-only shadow cycle;
- legacy 12-role packet -> 6-domain adapter;
- shadow CLI that reads `knowledge/candidates` + an agent-packet run and emits JSON to stdout only;
- offline runtime validator.

Local isolated validation of the exact staged Python implementation reached **12/12 tests PASS** before upload. This is not yet a claim that the code passes against the latest moving `main`; that reconciliation/integration test remains required before activation.

**No existing `control/hourly/*`, bridge, Recon, Weather or active runtime file is being modified by this lane during sidecar construction.** Integration into those files is deliberately deferred.

## Coordination rules for other sessions

1. **Do not merge either Research OS branch into `main` yet.** Both branches intentionally trail active `main` work and must be reconciled against a fresh `main` immediately before integration.
2. Continue normal work on `main`. Do not stop active Weather, Recon, bridge, executor or control-plane work because of this design.
3. Before modifying orchestration/candidate/evidence/scheduler semantics, re-read this coordination marker and current `main`.
4. If you change `control/hourly/agent_orchestrator.py`, `candidate_queue.py`, `packet_hydrator.py`, `hourly_cycle.py`, `recon_engine.py`, AI transport/bridge files, candidate schema/state semantics, or provenance/gating behavior, treat that as an integration input to Research OS V1.
5. Prefer additive, backward-compatible changes on `main`; avoid deleting legacy role semantics solely because Research OS V1 plans to consolidate them.
6. **Do not create competing `control/research_os_v1/*` implementations on `main` while this marker is IN PROGRESS.** If an urgent fix genuinely belongs there, preserve it and flag the overlap in this file or an adjacent coordination note rather than silently duplicating the feature.
7. Preserve `NO_PROVEN_EDGE`, point-in-time, provenance, negative evidence, no-post-hoc-relaxation and execution-realistic gates.
8. Do not introduce paid API/model calls, live trading, wallet/fund movement or hidden cost paths.
9. If a new `main` change supersedes part of the Research OS design, keep the stronger/newer implementation during reconciliation; never overwrite newer working Recon/Weather/bridge behavior with the older branch copy.
10. If you discover a new architectural failure mode, add/propose it for Research OS Failure Memory instead of silently working around it.
11. Any session that needs to touch the eventual integration hook should assume **sidecar-first, shadow-only** until the preregistered benchmark passes.
12. The runtime staging branch is allowed to add only Research-OS-specific sidecar files/tests until reconciliation; it must not patch current hourly/bridge/Weather/Recon runtime files directly.

## Known overlap with current main

Current/recent `main` work already improves areas Research OS V1 also cares about, especially:

- Recon WATCH -> HUNT promotion and hunt-plan generation;
- independent-source/context checks;
- packet hydration and Recon triage routing;
- specialist worker wiring / role contracts;
- candidate queue handling and no-starvation behavior;
- AI bridge/result preservation and response transport;
- Weather E401 evidence integrity, synchronization and diagnostics.

Research OS V1 should wrap/generalize these improvements, not replace them with older versions.

## Cross-session conflict protocol

When Research OS is eventually integrated:

1. fetch/read the then-current `main` first;
2. compare every overlapping file against the Research OS branches;
3. preserve the newest tested `main` implementation by default;
4. port only the Research OS abstraction/hook needed around it;
5. run existing hourly/bridge/Recon/Weather tests **plus** Research OS tests;
6. if semantics conflict, fail closed and record the conflict rather than force-merging;
7. merge only after shadow behavior is validated.

This means concurrent sessions may keep producing useful work now without being frozen by the Research OS build.

## Integration strategy

Preferred integration is sidecar-first:

1. finish Research OS modules and tests on runtime staging;
2. reconcile against fresh `main` while preserving newer main behavior;
3. run prebuild + runtime offline validation;
4. run Research OS shadow decisions alongside the existing factory;
5. compare old vs new behavior on preregistered metrics;
6. run the preregistered 1–6 concurrency experiment where feasible;
7. only then make a small adapter/hook into the active hourly factory.

No automatic activation is authorized by this coordination file.

Economic default remains: `NO_PROVEN_EDGE`.
