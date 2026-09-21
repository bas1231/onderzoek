# Research OS V1 — coordination marker

Status: **IN PROGRESS / DESIGN + SHADOW IMPLEMENTATION ONLY**

Owner lane: Research OS V1 architecture consolidation

Design branch: `ai/research-os-v1-prebuild-spec`

Canonical runtime remains: `main`

Latest `main` observed by this lane during coordination refresh: `910c91bcf4e8089b14ebfc6bf4453cf05ff5e6da`.

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

The Research OS lane is now moving from design to a **sidecar shadow runtime** on `ai/research-os-v1-prebuild-spec`.

Files/paths owned by this lane on the design branch:

- `control/research_os_v1/*`
- `benchmarks/research_os_v1/*`
- `docs/RESEARCH_OS_V1_*`
- `docs/PLUS_NATIVE_RESEARCH_OS_CANARY.md`
- Research-OS-specific tests to be added under `tests/` without replacing current hourly/bridge tests.

The shadow runtime being implemented contains:

- deterministic policy loader and Governor;
- canonical candidate adapter;
- reusable Failure Memory;
- minimal Evidence Graph;
- task-shape classifier / ordinal scheduler;
- worker task/result contract validation;
- read-only shadow-cycle that produces recommendations/artifacts only;
- tests for fail-closed behavior, anti-overkill behavior and concurrency policy.

**No existing `control/hourly/*`, bridge, Recon, Weather or runtime file is being modified by this lane during sidecar construction.** Integration into those files is deliberately deferred.

## Coordination rules for other sessions

1. **Do not merge `ai/research-os-v1-prebuild-spec` into `main` yet.** The branch intentionally trails active `main` work and must be reconciled against a fresh `main` immediately before integration.
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
2. compare every overlapping file against the Research OS branch;
3. preserve the newest tested `main` implementation by default;
4. port only the Research OS abstraction/hook needed around it;
5. run existing hourly/bridge/Recon/Weather tests **plus** Research OS tests;
6. if semantics conflict, fail closed and record the conflict rather than force-merging;
7. merge only after shadow behavior is validated.

This means concurrent sessions may keep producing useful work now without being frozen by the Research OS build.

## Integration strategy

Preferred integration is sidecar-first:

1. finish Research OS modules and tests on the design branch;
2. reconcile against fresh `main`;
3. run offline validation;
4. run shadow decisions alongside the existing factory;
5. compare old vs new behavior on preregistered metrics;
6. only then make a small adapter/hook into the active hourly factory.

No automatic activation is authorized by this coordination file.

Economic default remains: `NO_PROVEN_EDGE`.
