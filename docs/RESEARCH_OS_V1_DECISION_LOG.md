# Research OS V1 — Architecture Decision Log

Status: **DESIGN MEMORY**

Purpose: prevent later sessions from reintroducing rejected complexity without new evidence.

## AD-001 — Do not keep 12 permanent agent roles

Decision: consolidate into six responsibility domains while retaining old expertise as capabilities/gates.

Reason: current roles overlap, compete for one-turn context, and role count is not equivalent to independent intelligence.

Reconsider only if benchmarks show a merged domain repeatedly misses a failure mode that a standalone worker uniquely catches.

## AD-002 — Do not run six workers merely because six domains exist

Decision: elastic task-shape-dependent concurrency.

Reason: sequential tasks gain no value from fanout, idle workers create speculative filler, and coordination consumes usage/context.

Reconsider only if concurrency benchmark shows fixed six-worker execution dominates across task shapes without quality regression.

## AD-003 — Keep two protected discovery lanes

Decision: Primary Scout and Recon Scout stay distinct.

Reason: high-quality conservative discovery and weak-signal/offensive reconnaissance have deliberately different search distributions. One mixed Scout risks either excessive noise or excessive conservatism.

Guard: measured overlap; two Scouts are not useful if they search the same sources.

## AD-004 — Reproducer is temporary, not permanent

Decision: instantiate only for serious survivors.

Reason: reproduction is a validation phase, not a continuous discovery discipline; permanent capacity would mostly idle or waste usage.

Strengthening: temporary reproduction must be more isolated than the old named role.

## AD-005 — Pre-Build Killer + Chief Falsifier become Red Team modes

Decision: `QUICK_KILL` and `DEEP_FALSIFICATION` under one Red Team responsibility.

Reason: objectives overlap but depth/trigger differs. Keep both procedures, remove permanent duplicate role overhead.

## AD-006 — Settlement + Microstructure live under Mechanics

Decision: merge as capabilities, not checks.

Reason: contract meaning/finality and executable economics are tightly coupled. They remain separate subchecks inside Mechanics.

## AD-007 — Weather / Behavioral / Informed Flow live under Market Research

Decision: merge as modules/capabilities.

Reason: all answer variants of signal/predictive-information questions. Specialist context is selected dynamically.

## AD-008 — Algebra remains a first-class domain

Decision: do not bury formal payout reasoning in general Market Research.

Reason: statewise equivalence/dominance and theorem-style search are structurally different and benefit heavily from local exact computation.

## AD-009 — No full market digital twin in V1

Decision: minimal Evidence Graph only.

Reason: full venue/event/orderbook ontology is expensive and not necessary to solve the current highest-value coordination/provenance problems.

Reconsider when multiple real tasks are blocked by missing shared market-state representation.

## AD-010 — No dense agent debate or voting

Decision: sparse artifact-based communication and evidence adjudication.

Reason: agreement among correlated agents is not independent evidence; dense communication increases confirmation/majority pressure and coordination cost.

## AD-011 — No self-modifying methodology in V1

Decision: workers may propose methodology changes but cannot activate them.

Reason: an adaptive system could lower its own standards around favored hypotheses. Changes require versioned review and fresh benchmark evidence.

## AD-012 — No fake decimal Expected Information Gain

Decision: ordinal scheduling plus hard tie-breaks.

Reason: LLM-generated pseudo-precision would make subjective priorities look quantitative without calibrated probabilities/costs.

Reconsider only if empirical task-outcome data supports a calibrated learned scheduler.

## AD-013 — Failure Memory does not auto-kill by pattern name

Decision: pattern match opens a required check; factual confirmation can then kill/block.

Reason: superficial pattern similarity can differ materially in semantics. This protects novel edges from an overaggressive negative-memory system.

## AD-014 — KILL never means DELETE

Decision: preserve evidence and explicit kill/resurrection conditions.

Reason: venue rules, rewards, fees and market structure change. A previously dead route can become testable again without rewriting history.

## AD-015 — Director is orchestrator, not oracle

Decision: Director manages procedure/dependencies but cannot waive failed required gates.

Reason: central coordination is useful; central subjective truth authority is a single point of epistemic failure.

## AD-016 — Local deterministic compute before model tokens

Decision: hashes, change detection, dedupe, exact arithmetic, schema checks, exhaustive enumeration and replay should run locally when practical.

Reason: preserves Plus model allowance for ambiguity, synthesis, adversarial reasoning and experiment design.

## AD-017 — Plus-native five-slot design is a hypothesis, not dependency

Decision: canary native tasks; keep bridge/single-turn fallback.

Reason: Plus currently allows five active tasks and connected GitHub use, but exact read/write/context/scheduling behavior must be observed in this project.

## AD-018 — Do not pay to rescue capacity silently

Decision: no automatic credits/API/cloud upgrade.

Reason: user cost policy requires specific prior approval. Throughput may degrade; scientific rules may not.

## AD-019 — Separate mechanism, signal, market and execution

Decision: treat `mechanism` as an explicit layer before signal/market/execution.

Reason: algebraic/structural edges may not require predictive signal, while forecast improvements do. One mandatory linear pipeline would distort both.

## AD-020 — Current factory remains baseline until prospective evidence wins

Decision: shadow challenger first.

Reason: retrospective replay is contaminated by knowing historical outcomes. Architecture elegance is not evidence of superior research performance.

## AD-021 — Freeze matched-case benchmark rules before unseen shadow data

Decision: baseline and challenger must be scored on the exact same unique preregistered case IDs; missing or zero metric denominators remain `UNKNOWN`, never favorable zero; both sides must independently satisfy the minimum observation set.

Reason: the static V1 audit found that unmatched cases or denominator collapse could otherwise manufacture an apparent improvement without a real quality gain.

Timing: this amendment was made before the first unseen Research OS shadow observation was collected. It is therefore a preregistration hardening, not a post-result rule change.

Guard: `shadow_acceptance.json` schema V2 and `validate_prebuild_spec.py` now fail closed if these anti-gaming invariants are removed or weakened.
