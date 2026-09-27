# Research OS V1 — Pre-Build Audit

Status: **DESIGN PASS / RUNTIME ACTIVATION BLOCKED PENDING CANARY + SHADOW EVIDENCE**

Date: 2026-09-21

Design branch base at creation: `f9c1c973fbe0a96ca7791eb9c5f59d7e97b35946`

Important: `main` is actively changing in parallel. This branch is a design snapshot and must be reconciled against current `main` immediately before implementation. It must never overwrite newer Recon/Weather/control-plane work blindly.

## Executive conclusion

The strongest architecture is not twelve permanent agents and not six permanently busy agents.

The V1 target is:
- six responsibility domains;
- deterministic Governor;
- central Research Director;
- protected Primary + Recon discovery lanes;
- elastic specialist execution for Market Research / Mechanics / Algebra;
- Red Team with separated quick-kill and deep-falsification modes;
- temporary isolated Independent Reproducer;
- minimal Evidence Graph;
- machine-readable Failure Memory;
- hypothesis/search accounting;
- task-shape-aware scheduler;
- explicit resurrection conditions;
- shadow benchmark before migration.

The current factory remains the canonical runtime until the challenger proves it is better.

## Audit findings

### A1 — Current AI runtime is not real multi-worker execution

Current design explicitly hands one ACTIVE-HOUR bundle to a single ChatGPT research turn. Therefore the old 12-role registry must not be mistaken for 12 independent model workers.

Risk: role count can create the appearance of parallel intelligence while all reasoning competes inside one context/run.

V1 response: distinguish responsibility domains from runtime workers and benchmark real fan-out only when transport supports it.

### A2 — Candidate state is susceptible to split-brain

Current components use more than one candidate representation/root (`knowledge/candidates` and `candidates/active`). They may have intentional semantic differences, but a scheduler must not silently infer one unified truth from different universes.

Risk: Director routes from one state while memory/context describes another.

V1 response: canonical versioned candidate view with compatibility adapters.

### A3 — Current routing is mainly lexical/role based

Keyword routing is useful for bootstrap but does not encode dependency order, parallelism or the decisive uncertainty.

Risk: irrelevant specialist activation, duplicated work and sequential tasks fanned out too early.

V1 response: task-shape classifier plus explicit decisive question.

### A4 — Current queue priority is not information-sensitive enough

P0–P3 priority and age are useful operational controls but do not express whether a cheap source/semantic check can kill a route or whether a task unlocks multiple dependencies.

V1 response: frozen ordinal scheduler policy; age only as a late tie-break.

### A5 — Discovery coverage must be measured, not assumed

The bounded hourly source registry is a useful probe universe, not the whole public information space.

Risk: a healthy-looking hourly run can repeatedly cover the same easy sources while obscure but relevant areas remain unsearched.

V1 response: source-family coverage, changed-document count, primary ratio, Scout overlap and explicit coverage gaps.

### A6 — Failure knowledge exists but is not yet a first-class routing primitive

The negative-evidence ledger is strong, but many reusable failure modes still live as prose/history rather than machine-readable prechecks.

V1 response: 36 initial Failure Memory patterns. Pattern matches open a required check; they do not automatically kill unless the factual condition is proven.

### A7 — Multiple-testing rules exist methodologically but need enforced accounting

The methodology already requires explicit adaptive-search context, but every discovery pipeline must emit the search-family counters needed to enforce it.

V1 response: canonical search-family accounting on candidates/evidence.

### A8 — Independent reproduction needs stronger isolation

A named Reproducer role is insufficient if it sees the originating reasoning or shares the same derived upstream source.

V1 response: temporary blind/isolated reproduction and explicit source-independence status.

### A9 — Red Team must attack the process as well as candidates

False confidence can originate in routing, source overlap, shared data, selection bias or Director preference.

V1 response: methodology/process attack is a mandatory Red Team class for serious candidates and periodic system audits.

### A10 — Native Plus multi-lane execution is plausible but unproven

Plus currently provides up to five active Scheduled Tasks, but product behavior must be observed before treating tasks as reliable independent workers with shared Git state.

Unknowns requiring canary:
- connected GitHub read behavior in scheduled context;
- write capability/permission behavior;
- result/context isolation;
- practical scheduling order;
- retry/duplicate semantics;
- behavior near usage limits.

V1 response: five-slot canary with a bridge fallback; no API fallback without explicit approval.

### A11 — Main is changing concurrently

During this audit, newer Recon work landed on `main`, including a more conservative WATCH→HUNT promotion gate based on repeated observations, independent sources and economic context.

Risk: design branch can become stale while another session improves runtime.

V1 response: never merge this branch by overwrite. Before build, compare/rebase conceptually and retain newer main behavior unless an explicit V1 replacement passes equivalent tests.

### A12 — Architecture can become its own source of waste

Evidence graphs, schedulers and agent telemetry can consume more research capacity than they save.

V1 response: full market digital twin and self-modifying methodology are explicit non-goals. Coordination overhead is a benchmark metric.

## Historical replay result

The mixed replay suite contains:
- 20 known negative/closed routes;
- active maker-hedge survivor;
- payoff-identity discovery family;
- Weather E401 prospective survivor.

Coverage result: all known decisive historical failures can be mapped to an explicit V1 failure pattern/gate **without requiring an additional permanent role**.

Anti-overkill result: active survivors map to `WAITING/RUNNING` behavior rather than automatic kill. V1 explicitly treats waiting for prospective data as a reason to release AI capacity, not a reason to close the candidate.

This is a design-coverage PASS, not prospective proof that V1 is superior.

## Architecture Red Team

The pre-build suite currently contains 40 scenarios covering:
- state split-brain/concurrent writes;
- discovery starvation/duplication;
- Director and majority bias;
- Red Team/Reproducer contamination;
- sequential vs parallel task errors;
- prompt injection and unsafe/cost actions;
- lookahead/multiple testing/post-hoc changes;
- source conflict/disappearance;
- WS/REST/correlation evidence faults;
- scheduled-task failures, duplication and usage limits;
- context overflow and self-inflicted control-plane bloat.

V1 is not activation-ready until each scenario has either a deterministic response or a deliberately bounded UNKNOWN/fail-closed outcome.

## Pre-build decisions now frozen

1. Six responsibility domains; no automatic seventh permanent agent.
2. Independent Reproducer is temporary and isolated.
3. Governor is deterministic and outside model reasoning.
4. Two protected discovery lanes remain separate.
5. Specialists are dynamically scheduled by task shape.
6. Failure Memory is a precheck/required-test generator, not a blind kill engine.
7. Minimal Evidence Graph only; no V1 digital twin.
8. Scheduler uses ordinal criteria, not fake decimal expected values.
9. Search-family accounting is mandatory.
10. `KILL` never deletes history; changed decisive conditions can trigger resurrection.
11. No migration until unseen shadow data beats baseline under frozen metrics.
12. No paid API/model infrastructure, live trading or wallet actions are introduced.

## Remaining blockers before implementation

### BLOCKER B1 — reconcile with moving main

Fetch current main and map all changes since the design branch base, especially Recon, Weather, control-plane and queue changes.

### BLOCKER B2 — schema/spec consistency check

Validate JSON schemas/policies and build a non-runtime validator that catches missing IDs, invalid edge types, unknown Failure Pattern references and policy contradictions.

### BLOCKER B3 — Plus-native transport canary

Test only after the architecture is accepted. Do not assume GitHub task writes or timing behavior.

### BLOCKER B4 — current-vs-V1 shadow adapter

Build a shadow adapter that consumes the same evidence but cannot change canonical decisions. It must write separate challenger artifacts.

### BLOCKER B5 — unseen benchmark

Run the frozen acceptance criteria on unseen candidate events/task shapes. Historical replay alone cannot authorize migration.

## Go / No-Go

### GO now
- keep this branch as the frozen V1 design baseline;
- continue normal research on current `main`;
- use the failure suite and mixed replay as implementation tests;
- reconcile new runtime improvements into the build plan later.

### NO-GO now
- do not replace the current hourly factory;
- do not reduce gates because roles are merged;
- do not activate five scheduled tasks based only on product documentation;
- do not create paid/OpenAI API worker infrastructure;
- do not call the design prospectively superior yet.

## Economic conclusion

`NO_PROVEN_EDGE`.
