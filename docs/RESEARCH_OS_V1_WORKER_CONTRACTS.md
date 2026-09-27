# Research OS V1 — Worker Contracts

Status: **SHADOW DESIGN**

These contracts define what each responsibility receives, what it must not receive, and what a valid result looks like. The goal is to spend model context on the decisive problem rather than loading every worker with the entire repository.

## Shared rules for every worker

Every worker receives:
1. stable task ID and source commit/candidate version;
2. one explicit objective and decisive question;
3. only the relevant Evidence Graph subgraph and source artifacts;
4. applicable negative-evidence / Failure Memory patterns;
5. point-in-time cutoff and source policy;
6. hard Governor constraints;
7. required output schema and stop conditions.

Every worker must:
- preserve uncertainty as UNKNOWN rather than fill gaps;
- distinguish observation, inference and hypothesis;
- cite/provenance every material evidence item;
- record contradictions rather than merge them away;
- return `NO_NEW_EVIDENCE` when that is the correct outcome;
- never infer economic edge from model confidence alone.

No worker receives the full repository by default. Context expansion is dependency-driven.

---

## 1. PRIMARY_SCOUT

### Purpose

Maximize high-quality novel information inflow from official/primary/academic/code sources.

### Required context

- source-family coverage debt;
- change/hash summary from local deterministic ingest;
- active candidate mechanism keywords only when useful for targeted discovery;
- recent evidence fingerprints to prevent duplicates;
- relevant known negatives when a discovered mechanism resembles an old route.

### Do not preload

- full reasoning histories of every candidate;
- Red Team conclusions;
- verbose hourly reports when fingerprints/status suffice;
- raw unchanged documents.

### Search behavior

Breadth-first first, then narrow. Search across distinct source families. Prefer changed/new primary material. A repeated source with unchanged content is not a new finding.

### Valid result

For every finding:
- source + retrieval time/hash;
- exact new/changed fact;
- why it could matter;
- whether it duplicates known memory;
- candidate/mechanism relation if any;
- next verification step;
- confidence/status limited to evidence quality, not economic profitability.

### Stop rule

Stop a lane when marginal retrievals are duplicates/unchanged or no longer decision-relevant; move to the highest coverage-debt family.

---

## 2. RECON_SCOUT

### Purpose

Find weak signals and strange economic mechanisms that a conservative source sweep systematically misses.

### Required context

- Recon mechanism classes;
- WATCH/HUNT memory and kill/resurrection conditions;
- source overlap fingerprints from Primary Scout;
- coverage debt for incidents/community/obscure venues/code;
- safety boundary: public/legal intelligence only.

### Search behavior

Seek:
- recurring public reports of losses, adverse selection or failure;
- changed/unusual fees, rewards, collateral, settlement or lifecycle behavior;
- obscure/new market products;
- crowd/behavioral anomalies;
- public code/implementation artifacts;
- independently repeated weak signals.

Community/anecdotal material remains discovery-only until independently supported.

### Diversity constraint

Recon must not simply repeat Primary Scout queries. Cross-scout overlap is measured and penalized as duplicate research.

### Valid result

`DISCOVER`, `WATCH`, `HUNT` or `KILL_CURRENT_ROUTE` only with explicit evidence conditions. `HUNT` means targeted falsification is warranted, not edge proven.

---

## 3. SPECIALIST_DISPATCH

This slot dynamically instantiates one of three specialist capability modes.

### A. MARKET_RESEARCH mode

Use for forecast/signal, Weather, behavioral or informed-flow questions.

Required output separates:
- mechanism plausibility;
- signal evidence;
- out-of-sample status;
- search/multiple-testing context;
- whether a market mispricing has actually been shown.

A better forecast is not automatically market edge.

### B. MECHANICS mode

Use for rules, settlement, finality, fees, microstructure and execution.

Preferred order:
1. exact contract/rule/source semantics;
2. lifecycle/finality/exception classes;
3. executable bid/ask/depth/fees;
4. fill/queue/partial-fill/latency/capital assumptions;
5. worst-case net cashflow.

If an early semantic check kills the route, stop before expensive execution research.

### C. ALGEBRA mode

Use for statewise payouts, equivalence, dominance, synthetic portfolios and formal relations.

Local deterministic enumeration/theorem tools should do bulk exact search where practical. Model reasoning focuses on representation, relation families, missing states and adversarial counterexamples.

Formal identity produces `STRUCTURAL_CANDIDATE`; pricing/execution remains separate.

### Dispatch rule

Only one mode receives the slot unless the task shape explicitly justifies independent parallel specialist work through another available Work/agent path. `WAITING_FOR_DATA` is a valid result that releases the slot.

---

## 4. RED_TEAM

### Purpose

Try to invalidate the candidate or the research process using different failure modes.

### Blind input policy

Prefer:
- concise claim;
- primary evidence refs;
- rules/data;
- explicit assumptions;
- required gates.

Avoid where feasible:
- original persuasive thesis narrative;
- originating worker confidence;
- desired conclusion;
- selected quotes that omit counterevidence.

### Mandatory attack families

1. semantic/source;
2. point-in-time/revision/leakage;
3. logical/mechanism counterexample;
4. statistical/multiple-testing/dependence;
5. market/execution/friction;
6. regime/robustness;
7. process/selection/independence.

Not every family applies to every candidate, but `NOT_APPLICABLE` must be reasoned rather than omitted.

### Valid verdicts

- `KILL`
- `PARK`
- `NEEDS_EVIDENCE`
- `SURVIVED_RED_TEAM`

`SURVIVED_RED_TEAM` is not promotion or proof of edge.

---

## 5. RESEARCH_DIRECTOR

### Purpose

Orchestrate; do not become a seventh all-purpose analyst that redoes every worker's work.

### Inputs

- validated worker artifacts;
- canonical candidate versions;
- dependency/gate state;
- source coverage and duplicate metrics;
- queue and waiting conditions;
- Governor decisions;
- current Git commit/version.

### Responsibilities

- reject stale/conflicting worker results until reconciled;
- update dependency/gate state;
- choose next decisive question using frozen scheduler policy;
- preserve discovery capacity;
- route WAITING candidates without wasting AI;
- trigger Red Team / Reproducer only when justified;
- report explicit `NO_NEW_EVIDENCE` lanes;
- publish consolidated status without converting research-positive evidence into economic proof.

### Director anti-bias rule

Every serious promotion path must contain a falsification artifact not authored by the same reasoning path that proposed the candidate.

Director may adjudicate evidence/procedure; it may not waive a required failed gate.

---

## 6. TEMPORARY INDEPENDENT_REPRODUCER

### Trigger

Spawn only when independent reproduction can change a promotion gate.

### Blindness

Provide:
- preregistered question/test;
- raw/primary required data and rules;
- point-in-time cutoff;
- acceptance criteria.

Hide where feasible:
- original implementation details;
- originating reasoning chain;
- expected result;
- confidence language.

### Independence declaration

Result must classify:
- model/prompt independence;
- implementation independence;
- upstream data/source independence.

Shared upstream evidence prevents a claim of fully independent replication.

---

## Context-budget principle

Do not measure worker quality by prompt size. The target is **maximum relevant evidence and reasoning space per task**.

Context packing order:
1. objective / decisive question;
2. Governor + point-in-time constraints;
3. primary evidence necessary to answer it;
4. relevant graph dependencies;
5. applicable Failure Memory;
6. compact prior result summaries only where dependency requires them;
7. optional broader context last.

If context grows too large, split by independent subquestion or retrieve artifacts on demand. Never silently drop contradictory evidence merely to fit context.

## Model-capability principle

Scientific contracts are model-agnostic. When Plus/Work offers multiple capability levels, allocate strongest reasoning to Director adjudication, deep Red Team, Algebra/formal reasoning and blind reproduction; use faster modes for source triage after deterministic filtering where quality is preserved.

Model availability or usage limits may reduce throughput. They may not reduce evidence standards.
