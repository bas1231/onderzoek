# E007 — Six-Domain Research OS Architecture

Status: NORMATIVE TARGET SPECIFICATION
Branch: `ai/research-os-six-domain-e007`
Production target: `main` only after implementation and required regression/canary gates pass.

## 1. Goal

Replace the current twelve permanent runtime roles with six permanent Research OS domains while preserving the proven specialist logic as capabilities. Reduce fragmentation, increase useful context per active worker, keep discovery diversity, and preserve deterministic safety/provenance gates.

This is a runtime architecture change, not a reduction in research scope.

## 2. Permanent agents

Exactly six permanent runtime agents exist after E007:

1. `discovery`
   - capabilities: `scout`, `recon_scout`
   - two protected lanes remain separate: `primary_scout` and `recon_scout`
   - purpose: broad discovery plus independent offensive economic reconnaissance

2. `market_research`
   - capabilities: `weather_twc`, `behavioral`, `informed_flow`
   - purpose: market-domain evidence, nowcasting/weather/TWC, behavioral mechanisms, informed-flow signatures

3. `mechanics`
   - capabilities: `settlement`, `microstructure`
   - purpose: rules, settlement/finality/revision, orderbook, executable fills, fees, depth, slippage, latency and partial-fill reality

4. `algebra`
   - capabilities: `algebra`
   - purpose: statewise payout proofs, contract equivalence, synthetic portfolios and formal market algebra

5. `red_team_pentest`
   - capabilities: `prebuild_killer`, `chief_falsifier`
   - modes: `QUICK_KILL`, `DEEP_FALSIFICATION`
   - purpose: cheapest decisive kill first; deeper adversarial falsification only for serious survivors

6. `research_director`
   - capability: `research_director`
   - purpose: scheduling, routing, deterministic gates, lifecycle coordination, hourly status and resource allocation

The old specialist identities are capabilities, not permanent workers.

## 3. Transient Independent Reproducer

`independent_reproducer` is not a seventh permanent agent.

It is spawned only when a candidate is a serious survivor and independent reproduction is required by the proof gate. It must be blind to the originating worker's conclusion except for the minimum preregistered hypothesis/test interface needed to reproduce the claim.

The reproducer has `VALIDATION_ONLY` authority and no promotion, trading, payment or wallet authority.

## 4. Protected Discovery architecture

Discovery retains two logically independent lanes even though one permanent `discovery` packet/worker owns both:

- `primary_scout`: broad source/evidence discovery
- `recon_scout`: offensive search for mechanism weaknesses, failures, anomalies, counter-crowd signals and neglected public information

Rules:
- provenance is stored separately per lane;
- outputs are separately labelled by lane;
- one lane may not silently overwrite/deduplicate the other before Director review;
- agreement is evidence convergence, not permission to double-count correlated evidence;
- disagreement is preserved as useful negative/uncertainty evidence.

## 5. Dynamic worker pool

The Director is not counted as a specialist worker.

The five non-Director domains form the dynamic worker pool:
- discovery
- market_research
- mechanics
- algebra
- red_team_pentest

At most five can be active simultaneously. A domain is scheduled only when it has admissible work.

No permanent worker must produce filler output merely because an hourly cycle exists.

## 6. Task-shape concurrency

Every scheduled work item is classified before dispatch:

- `LOW_SEQUENTIAL`
  - max internal parallelism: 1
  - use for tightly dependent chains, Red Team kill/falsification and blind reproduction

- `MEDIUM_PARTIAL`
  - max internal parallelism: 3
  - use for partially independent evidence/mechanics questions

- `HIGH_INDEPENDENT`
  - max internal parallelism: 5
  - use for genuinely independent candidate/source/capability work

Concurrency is a ceiling, not a target. Dependencies override parallelism.

## 7. Scheduler priority

The deterministic scheduler uses this order:

1. `GOVERNOR_ADMISSIBLE_ONLY`
2. `DECISIVE_SEMANTIC_OR_SOURCE_KILL_CHECK`
3. `CHEAP_DECISIVE_FALSIFICATION`
4. `POINT_IN_TIME_OR_EXECUTION_EVIDENCE`
5. `MULTI_DEPENDENCY_UNLOCK`
6. `TIME_SENSITIVE_EVIDENCE`
7. `NOVEL_EVIDENCE`
8. `AGE_TIE_BREAK`

The goal is decision value, not agent utilization.

## 8. Candidate routing

E006 remains the semantic-routing foundation but routes capabilities into six domain packets.

Required mapping:
- Scout/Recon semantics -> `discovery` with capability/lane labels
- Weather/TWC/behavioral/informed-flow -> `market_research`
- Settlement/finality/revision/execution/L2/fills/slippage -> `mechanics`
- Statewise payoff/equivalence -> `algebra`
- Kill/falsification work -> `red_team_pentest`
- Coordination/gates -> `research_director`

A candidate may route to multiple domains when independently justified by semantics.

Routing must remain deterministic, auditable and non-hardcoded to specific candidate IDs.

`PARKED` and `CLOSED_NEGATIVE` candidates must not be silently reactivated.

## 9. Capability separation inside domain packets

When several legacy capabilities share one domain packet, work remains structurally separated under `capability_work` (or equivalent explicit substructure).

Examples:
- `market_research.weather_twc`
- `market_research.behavioral`
- `market_research.informed_flow`
- `mechanics.settlement`
- `mechanics.microstructure`
- `red_team_pentest.prebuild_killer`
- `red_team_pentest.chief_falsifier`

A consolidated agent may synthesize across capabilities only after preserving source provenance and capability-specific findings.

## 10. Red Team/Pentest lifecycle

Red Team has two deterministic stages:

### QUICK_KILL
Run early and cheaply. Target obvious fatal flaws, including:
- settlement/source mismatch;
- hidden exception classes;
- non-executable prices;
- stale/cache/UI evidence;
- theoretical identity with no economic edge;
- gross edge destroyed by fees/spread/slippage;
- lookahead/revision leakage;
- post-hoc gate relaxation;
- capacity/depth collapse;
- known Failure Memory patterns.

### DEEP_FALSIFICATION
Only serious survivors receive deeper adversarial testing. Attack assumptions, source independence, execution reality, point-in-time integrity and robustness.

Red Team can recommend veto/falsification but does not independently promote candidates or authorize live actions.

## 11. Evidence Graph and Failure Graph

E007 target includes persistent graph-style memory, even if implemented over existing JSON stores initially.

Evidence Graph must preserve:
- candidate -> claim -> evidence links;
- source and retrieval point-in-time;
- specialist/capability provenance;
- corroboration and contradiction;
- execution evidence vs semantic evidence;
- negative evidence;
- reproduction evidence.

Failure Graph must preserve:
- known failure-pattern IDs;
- candidate encounters with those patterns;
- decisive negative results;
- killed/parked reasons;
- resurrection conditions;
- shared root causes across candidates.

KILL != DELETE. Negative evidence remains queryable and can block repeated dead ends.

## 12. Lifecycle and proof chain

Default economic conclusion remains `NO_PROVEN_EDGE`.

A typical candidate path is:

Discovery/Research -> capability/domain evidence -> QUICK_KILL -> decisive tests -> DEEP_FALSIFICATION -> transient blind Independent Reproducer -> deterministic proof gate -> promotion candidate.

No single AI worker can self-promote a hypothesis to proven edge.

Independent reproduction is necessary for serious promotion, not for every early idea.

## 13. Deterministic proof/economic gate

AI reasoning may propose findings, tests and candidate lifecycle recommendations, but machine gates own promotion admissibility.

At minimum, a promoted economic-edge candidate must have the required applicable gates for:
- source provenance;
- point-in-time integrity;
- out-of-sample/prospective evidence where applicable;
- signal edge;
- market edge;
- execution reality;
- Red Team survival;
- independent reproduction;
- fees;
- spread;
- slippage;
- fills/partial fills;
- settlement/finality;
- capacity.

Economic evaluation remains based on execution-realistic net edge, not UI/midpoint/gross theoretical edge.

## 14. Safety invariants

The following are hard invariants and must remain false unless the user separately gives explicit approval for a specific action:

- `live_trading = false`
- `paid_actions = false`
- `wallet_actions = false`
- `openai_api = false`

E007 does not authorize:
- live orders/trades;
- wallet/crypto movements;
- paid APIs, datasets, subscriptions or cloud resources;
- autonomous candidate promotion outside machine gates;
- autonomous candidate deletion that destroys negative evidence.

## 15. Existing production infrastructure that must survive E007

The migration must preserve:
- canonical candidate queue;
- E006 semantic candidate routing guarantees;
- V16 response return/durable receipt/checkpoint behavior;
- Git provenance and durable run artifacts;
- response-token/run-id integrity;
- fail-closed behavior on invalid responses;
- `NO_PROVEN_EDGE` default;
- no silent waiting/zombie candidate behavior;
- explicit safety flags.

## 16. Required runtime flow after E007

Target hourly flow:

1. create six permanent domain packets;
2. source sweep and point-in-time ingestion;
3. keep Discovery lanes separate;
4. build one canonical candidate-queue snapshot;
5. route evidence/candidates into capabilities within domain packets;
6. run QUICK_KILL assignment where appropriate;
7. classify task shape;
8. schedule only useful domain workers, max five specialists;
9. build one AI work bundle;
10. receive/validate one response tied to run-id/response-token;
11. apply candidate decisions only within allowed lifecycle states;
12. update Evidence/Failure Graph state;
13. spawn blind transient Reproducer only for qualifying survivors;
14. enforce deterministic proof/economic gates;
15. durable receipt/checkpoint to `main`;
16. Research Director publishes cycle status.

## 17. Migration acceptance criteria

E007 is implementation-complete only when all of the following are true:

- registry creates exactly six permanent agents;
- no old specialist except `algebra`/`research_director` remains a separate permanent packet;
- all old specialist functionality is represented as a domain capability;
- Discovery has two protected provenance lanes;
- real E006 candidate semantics route to the correct new domain/capability;
- consolidated packets preserve candidate IDs and capability provenance into AI exchange;
- task-shape scheduler enforces 1/3/5 limits and max five specialist domains;
- Red Team supports QUICK_KILL and DEEP_FALSIFICATION;
- Independent Reproducer is transient and blind, not permanent;
- Evidence/Failure Graph state is persistent and preserves negative evidence;
- AI response validation accepts only the new permanent role IDs plus valid transient Reproducer responses;
- V16 durable return/receipt/checkpoint still works;
- safety invariants remain false;
- no candidate is silently lost, duplicated, reactivated from terminal state, or promoted without required gates.

## 18. Production activation rule

Do not switch `main` to E007 merely because the design is conceptually superior.

The branch may replace the current shadow baseline after the migration wiring is complete and minimum regression/canary checks demonstrate that routing, AI exchange, response ingestion and durable checkpointing still function.

Once merged, previous shadow benchmark counts should be treated as the old-architecture baseline; E007 starts its own prospective shadow cohort.

## 19. Source of truth

This document is the normative E007 architecture specification.

Implementation files such as `agents/registry.json`, `control/hourly/research_os_architecture.py`, routing, scheduler, AI handoff and response validation must conform to this document. If code and this specification disagree during E007 development, fix the code or explicitly amend this document before production activation.
