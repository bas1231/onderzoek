# Research OS V1 — coordination marker

Status: **IN PROGRESS / DESIGN + SHADOW IMPLEMENTATION ONLY**

Owner lane: Research OS V1 architecture consolidation

Design branch: `ai/research-os-v1-prebuild-spec`

Canonical runtime remains: `main`

## Purpose

This file exists so other active sessions working on `main` can see that a Research OS V1 redesign is being prepared in parallel and can avoid duplicating or conflicting work.

The redesign consolidates the current agent layer into six responsibility domains while preserving existing specialist checks as capabilities/gates:

1. Discovery
2. Market Research
3. Mechanics
4. Algebra
5. Red Team / Pentest
6. Research Director

Independent Reproduction remains a temporary isolated validation step rather than a permanent seventh role.

## Core architecture under construction

The design branch currently contains:

- deterministic Governor for cost/live/wallet/safety/point-in-time invariants;
- Primary Scout + Recon Scout protected discovery lanes;
- dynamic specialist dispatch instead of permanently active specialist agents;
- task-shape classification for sequential vs partial vs independent work;
- canonical candidate view;
- minimal Evidence Graph;
- reusable Failure Memory derived from historical negative evidence;
- hypothesis/multiple-testing accounting;
- ordinal information-gain-style scheduling without fabricated decimal scores;
- protected discovery capacity and exploration budget;
- blind(er) Red Team and temporary Independent Reproducer;
- architecture red-team scenarios;
- historical replay benchmark including both negatives and anti-overkill survivor cases;
- 1–6 worker concurrency benchmark;
- Plus-native topology/canary design;
- staged rollout and rollback plan;
- offline pre-build validator.

## Coordination rules for other sessions

1. **Do not merge `ai/research-os-v1-prebuild-spec` into `main` yet.** The branch intentionally trails active `main` work and must be reconciled after concurrent Recon/Weather/control-plane development settles.
2. Continue normal work on `main`. Do not stop active Weather, Recon, bridge, executor or control-plane work because of this design.
3. If you change agent orchestration, packet hydration, candidate state, scheduler semantics, Recon promotion, evidence/provenance handling or bridge/task transport, treat that as potentially relevant to Research OS V1.
4. Prefer additive, backward-compatible changes on `main`; avoid deleting legacy role semantics solely because Research OS V1 plans to consolidate them.
5. Preserve `NO_PROVEN_EDGE`, point-in-time, provenance, negative evidence, no-post-hoc-relaxation and execution-realistic gates.
6. Do not introduce paid API/model calls, live trading, wallet/fund movement or hidden cost paths.
7. If a new `main` change supersedes part of the Research OS design, keep the stronger implementation and update the eventual reconciliation rather than duplicating it.
8. If you discover a new architectural failure mode, add or propose it for the Research OS Failure Memory instead of silently working around it.

## Known overlap with current main

Recent `main` work already improves areas Research OS V1 also cares about, especially:

- Recon WATCH -> HUNT promotion;
- independent-source/context checks;
- packet hydration;
- specialist worker wiring;
- candidate queue handling;
- AI bridge/result preservation;
- Weather E401 evidence integrity and synchronization diagnostics.

Research OS V1 should wrap and generalize these improvements, not replace them with older versions.

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
