# Research OS V1 — No-Regression Rollout Plan

Status: **PLAN ONLY — CURRENT FACTORY REMAINS CANONICAL**

## Principle

Do not perform a big-bang rewrite. Introduce Research OS as a read-only/shadow challenger around the existing factory, preserve all current evidence, and promote components only after their own no-regression gate passes.

## Phase 0 — Reconcile moving `main`

Before writing runtime code:
1. compare current `main` against the design branch base;
2. inventory Recon, Weather, queue, bridge and methodology changes;
3. map every newer behavior to `KEEP`, `ADAPT`, or `SUPERSEDE_WITH_TEST`;
4. never overwrite newer runtime code from this design snapshot.

Special attention: current Recon already has quality filtering, WATCH/HUNT state, independent-source requirements, resurrection and targeted hunt plans. V1 should consume these as evidence/routing improvements rather than rebuild them blindly.

Exit gate: written reconciliation with no unresolved conflicting behavior.

## Phase 1 — Spec validator and canonical read adapter

Build only read-only infrastructure:
- run `validate_prebuild_spec.py` locally;
- add tests for all machine-readable specs;
- create a canonical candidate read adapter over existing candidate stores;
- detect split-brain versions; do not write/migrate records yet;
- expose source commit/version in every read.

Exit gate:
- validator PASS;
- no runtime behavior change;
- canonical adapter reproduces existing candidate states or reports explicit differences.

## Phase 2 — Failure Memory shadow precheck

Run Failure Memory against existing candidate/evidence packets without changing queue decisions.

Measure:
- patterns triggered;
- false pattern matches;
- decisive checks suggested earlier than current pipeline;
- survivors incorrectly threatened by pattern matches.

Exit gate: no automatic kill is permitted; Red Team review confirms pattern applicability logic.

## Phase 3 — Task-shape and scheduler shadow

For every current factory decision, V1 independently emits:
- decisive question;
- task shape;
- selected worker domain;
- proposed fanout;
- priority rationale;
- next task.

It may not change the canonical queue.

Compare against current P0/P1/age scheduler using frozen shadow metrics.

Exit gate: enough unseen cases to satisfy `shadow_acceptance.json` minimum observation set; no hard-fail condition.

## Phase 4 — Evidence Graph shadow writes

Write only challenger graph artifacts in a dedicated namespace/branch.

Requirements:
- idempotent node/edge IDs;
- source commit and provenance;
- contradictory evidence preserved;
- no inference treated as primary evidence;
- graph loss never deletes canonical Git evidence.

Exit gate: rebuild graph from source artifacts and obtain equivalent dependency state.

## Phase 5 — Consolidate legacy roles inside the existing transport

Before introducing parallel model workers, test the six-domain prompt/context design within the current single-turn transport.

Purpose: isolate the benefit of role consolidation/context targeting from the effect of adding more model calls.

Compare:
- context duplication;
- useful evidence density;
- missed mandatory checks;
- report completeness.

Exit gate: all legacy mandatory capabilities/gates still represented.

## Phase 6 — Plus-native transport canary

Use the dedicated canary plan. Start with non-sensitive, non-economic canary artifacts only.

Test:
- Scheduled Task GitHub read;
- task/project-file isolation;
- optional GitHub write behavior;
- idempotency;
- scheduling order;
- usage-limit behavior;
- bridge fallback.

No live strategy research depends on the canary until it passes.

Exit gate: documented product behavior, not assumptions.

## Phase 7 — Dual Discovery shadow

Run Primary Scout and Recon Scout as genuinely separate discovery lanes where the proven transport allows it.

Do not yet parallelize all specialists.

Measure:
- unique relevant evidence;
- source-family coverage;
- cross-scout duplicate ratio;
- unsupported weak-signal rate;
- coverage debt.

Exit gate: dual discovery adds novel useful evidence at acceptable duplication/usage cost.

## Phase 8 — Dynamic Specialist + Red Team shadow

Introduce task-shape-dependent specialist execution and isolated Red Team.

Sequential tasks remain sequential. Only distinct independent subquestions fan out.

Exit gate: concurrency experiment supports chosen fanout; no increase in false survivors or premature kills.

## Phase 9 — Temporary blind reproduction

Add temporary reproducer only for a serious candidate whose promotion state can change.

Require explicit independence declaration.

Exit gate: shared-upstream tests prove the system refuses false independence.

## Phase 10 — Director challenger decision

The V1 Director may now produce a complete shadow decision and next-hour plan, but current factory remains authoritative for the comparison period.

Exit gate: `shadow_acceptance.json` replacement rule passes on unseen cases.

## Phase 11 — Controlled cutover

Only after acceptance:
- make V1 scheduler/canonical view authoritative;
- retain old factory in rollback mode initially;
- preserve all old role artifacts and negative evidence;
- keep Governor fail-closed;
- migration commit/PR must show exact deleted/replaced pathways.

No trading permissions change as part of this cutover.

## Rollback rule

Any of the following immediately returns authority to the current factory or last-known-good control plane:
- candidate state inconsistency;
- provenance/point-in-time regression;
- repeated duplicate ingestion;
- required gate bypass;
- unexplained worker result loss;
- Plus task behavior inconsistent with canary assumptions;
- cost/live/wallet policy breach attempt.

## What is deliberately postponed

- full market digital twin;
- autonomous methodology mutation;
- unlimited subagent spawning;
- model-voting systems;
- paid API worker farm;
- automatic strategy deployment.

## Success definition

Research OS succeeds only if it produces more decision-relevant, independently supported evidence per unit of model attention **without** weakening falsification, provenance, survivor preservation or safety/cost controls.

Economic status remains `NO_PROVEN_EDGE`.
