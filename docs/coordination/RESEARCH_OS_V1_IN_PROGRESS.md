# Research OS V1 — coordination marker

Status: **V1 SIDECAR CODE COMPLETE / FRESH-MAIN SHADOW INTEGRATION / NOT ACTIVE**

Owner lane: Research OS V1 architecture consolidation

Design branch: `ai/research-os-v1-prebuild-spec`

Legacy runtime staging branch: `ai/research-os-v1-runtime-staging` — superseded for integration purposes

Primary integration branch: `ai/research-os-v1-integration-shadow`

Primary draft PR: **#21** — `Research OS V1 — fresh-main shadow integration (draft)`

PR #20 is closed/superseded.

Canonical active runtime remains: `main`.

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

Research OS V1 is now implemented as an **additive sidecar shadow runtime** on `ai/research-os-v1-integration-shadow`.

That branch was created from then-current `main`, after the concurrent Recon/Weather/bridge changes, and Research OS paths were overlaid without modifying existing runtime files. At the clean integration check it was ahead of `main` and not behind it.

Paths owned by this lane:

- `control/research_os_v1/*`
- `benchmarks/research_os_v1/*`
- `docs/RESEARCH_OS_V1_*`
- `docs/PLUS_NATIVE_RESEARCH_OS_CANARY.md`
- `tests/research_os_v1/*`

Implemented V1 functionality now includes:

- deterministic policy loader and Governor;
- canonical candidate adapter;
- 36-pattern Failure Memory: match -> required test, never automatic kill;
- minimal idempotent Evidence Graph with conflict rejection;
- worker task/result contract validation;
- ordinal scheduler and task-shape fanout caps;
- read-only shadow cycle and CLI;
- legacy 12-role packet -> 6-domain adapter;
- hypothesis/multiple-testing accounting;
- Primary/Recon source-family coverage and overlap accounting;
- deterministic promotion gate; Director cannot waive a required failed gate;
- explicit kill/resurrection handling; old validation is not inherited after regime change;
- blind Red-Team packet with fixed attack order;
- isolated Reproducer packet plus upstream-source-independence check;
- preregistered shadow benchmark metrics/replacement gate with no composite score and no automatic activation;
- offline prebuild/runtime validators;
- architecture red-team, historical replay and 1–6 concurrency benchmark specifications.

Validation history:

- earlier staged core reached **12/12 isolated local tests PASS** before fresh-main integration;
- the fresh integration branch contains additional methodology modules/tests and therefore still requires a new full local execution before PR #21 may leave draft;
- no GitHub Actions workflow / potentially billable CI was started.

**No existing `control/hourly/*`, bridge, Recon, Weather, executor or active-runtime file has been modified by Research OS V1.**

## Coordination rules for other sessions

1. **Do not merge PR #21 or activate Research OS yet.** It is a shadow sidecar until local tests + preregistered shadow acceptance pass.
2. Continue normal work on `main`. Do not stop active Weather, Recon, bridge, executor or control-plane work because of Research OS.
3. Before modifying orchestration/candidate/evidence/scheduler semantics, re-read this marker and current `main`.
4. If you change `control/hourly/agent_orchestrator.py`, `candidate_queue.py`, `packet_hydrator.py`, `hourly_cycle.py`, `recon_engine.py`, AI transport/bridge files, candidate schema/state semantics, or provenance/gating behavior, treat that as an integration input to Research OS V1.
5. Prefer additive, backward-compatible changes on `main`; avoid deleting legacy role semantics solely because Research OS plans to consolidate them.
6. **Do not create competing `control/research_os_v1/*` implementations on `main`.** If an urgent fix genuinely belongs there, flag the overlap here or in PR #21 instead of silently duplicating it.
7. Preserve `NO_PROVEN_EDGE`, point-in-time, provenance, negative evidence, no-post-hoc-relaxation and execution-realistic gates.
8. Do not introduce paid API/model calls, live trading, wallet/fund movement or hidden cost paths.
9. If a new `main` change supersedes part of Research OS, keep the stronger/newer `main` implementation during reconciliation; never overwrite newer working Recon/Weather/bridge behavior with an older branch copy.
10. If you discover a new architectural failure mode, add/propose it for Research OS Failure Memory rather than silently working around it.
11. Any session that needs to touch the eventual integration hook should assume **sidecar-first, shadow-only** until the preregistered benchmark passes.
12. The integration branch may add Research-OS-specific sidecar files/tests only until shadow acceptance; active hourly/bridge/Weather/Recon runtime patches belong in a later minimal-hook change.

## Known overlap with current main

Current/recent `main` work already improves areas Research OS V1 also cares about, especially:

- Recon WATCH -> HUNT promotion and hunt-plan generation;
- independent-source/context checks;
- packet hydration and Recon triage routing;
- specialist worker wiring / role contracts;
- candidate queue handling and no-starvation behavior;
- AI bridge/result preservation and response transport;
- Weather E401 evidence integrity, synchronization and diagnostics.

Research OS V1 wraps/generalizes these improvements; it must not replace them with older versions.

## Cross-session conflict protocol

Before any merge/integration:

1. fetch/read the then-current `main`;
2. ensure PR #21 is not behind; if it is, rebuild/reconcile its additive sidecar on fresh `main`;
3. preserve newest tested `main` implementation by default;
4. run existing hourly/bridge/Recon/Weather tests plus Research OS tests;
5. run prebuild/runtime validators;
6. run `shadow_cli` against current real agent packets and candidates without feeding output back;
7. if semantics conflict, fail closed and record the conflict rather than force-merging;
8. merge/activate only after shadow acceptance and a separate minimal-hook review.

## Remaining validation sequence

1. `pytest -q tests/research_os_v1`
2. `python -m control.research_os_v1.validate_prebuild_spec`
3. `python -m control.research_os_v1.validate_runtime`
4. regression tests for current hourly/bridge/Recon/Weather code
5. read-only real-packet shadow runs
6. at least 20 unseen candidate-events across at least 10 ACTIVE-HOUR cycles, with multiple task shapes, at least one survivor and one decisive negative
7. preregistered replacement-rule evaluation
8. only then a minimal active-factory hook

No automatic activation is authorized by this coordination file or PR #21.

Economic default remains: `NO_PROVEN_EDGE`.
