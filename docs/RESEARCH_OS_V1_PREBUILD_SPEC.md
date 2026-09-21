# Research OS V1 — Pre-Build Specification

Status: **DESIGN FROZEN FOR SHADOW BENCHMARK — NOT ACTIVE RUNTIME**

Date: 2026-09-21

Economic default: **NO_PROVEN_EDGE**

This document defines the smallest Research OS architecture that is allowed to enter shadow evaluation against the current hourly factory. It does not replace `main`, does not authorize live trading, does not authorize paid actions and does not authorize wallet actions.

## 1. Why this exists

The current hourly factory is scientifically disciplined, but the control plane still has four structural weaknesses:

1. the AI transport is one ChatGPT turn wearing multiple roles rather than independent workers;
2. routing is largely role/keyword based instead of dependency- and task-shape-aware;
3. queue priority is dominated by P0–P3 plus age instead of decision value and uncertainty reduction;
4. memory, candidates, negatives and claims are stored in several useful but partially separate representations.

V1 must improve those weaknesses without weakening any existing methodological gate.

## 2. Six responsibility domains

V1 has six durable responsibility domains. A responsibility is not necessarily a permanently running model worker.

1. `discovery` — primary-source discovery plus offensive economic reconnaissance.
2. `market_research` — signal, forecasting, behavioral and informed-flow research.
3. `mechanics` — rules, settlement, finality, fees, order book, fills and execution reality.
4. `algebra` — payout functions, equivalence, dominance, synthetic portfolios and theorem-style verification.
5. `red_team` — quick-kill, falsification, leakage attack, execution attack and methodology attack.
6. `research_director` — scheduling, dependency management, context allocation, gate enforcement and reporting.

`independent_reproducer` is not a seventh permanent domain. It is an isolated temporary worker instantiated only for serious survivors.

## 3. Protected discovery lanes

Discovery receives protected capacity during every ACTIVE-HOUR.

### Primary Scout

Priority order:
- official venue documentation, APIs, rulebooks, fees, rewards and changelogs;
- academic primary literature and public datasets;
- code repositories and public technical artifacts;
- reputable secondary sources.

### Recon Scout

Searches for weak signals that the Primary Scout will systematically under-sample:
- observed losses/failures and adverse-selection stories;
- strange or unintended economic mechanisms;
- obscure products and venue changes;
- behavioral/crowding signatures;
- incident and implementation evidence;
- community/code leads that require independent verification.

The two lanes must use different source/query families. Duplicate-source overlap is measured, not rewarded.

## 4. Dynamic workers, not six compulsory workers

Workers are allocated by task shape. A worker can be idle when no decisive task exists.

Normal target concurrency for the shadow design is **3–5 model workers**, not a fixed six. Higher fan-out requires an explicitly parallel task and must show incremental unique evidence. Sequential tasks must not be parallelized merely to increase activity.

Every task is classified on:
- `parallelism`: low / medium / high;
- `dependency_shape`: independent / partial / sequential;
- `uncertainty_type`: source / semantic / mechanism / signal / market / execution / robustness;
- `time_sensitivity`: low / medium / high;
- `novelty`: duplicate / incremental / novel;
- `decision_relevance`: low / medium / high / decisive;
- `evidence_cost`: low / medium / high;
- `model_cost`: low / medium / high.

## 5. Deterministic Governor

The Governor is code/policy, not an LLM opinion.

Hard invariants:
- paid action => `BLOCK_USER_APPROVAL`;
- live order/trade => `BLOCK_USER_APPROVAL`;
- wallet/fund movement => `BLOCK_USER_APPROVAL`;
- credential mutation or secret exfiltration => `BLOCK`;
- unauthorized access, fraud, manipulation, deception or active security exploitation => `BLOCK`;
- free/public/read-only research => allowed if provenance is preserved;
- later information may never be backfilled into a point-in-time decision;
- negative evidence may never be deleted to improve a thesis;
- failed gates may never be relaxed post hoc to obtain a positive result;
- economic status defaults to `NO_PROVEN_EDGE`.

No Director or worker may override a Governor decision.

## 6. Canonical state model

V1 must expose one canonical candidate view. Existing stores may remain for compatibility, but the control plane must not silently treat `knowledge/candidates` and `candidates/active` as different universes.

A canonical candidate has at minimum:
- stable `candidate_id`;
- hypothesis/mechanism;
- phase and queue state;
- claims and assumptions;
- supporting and contradictory evidence;
- explicit kill conditions;
- resurrection conditions;
- required gates;
- search-family / multiple-testing context;
- next decisive question;
- dependencies and blockers;
- point-in-time cutoff;
- provenance references.

## 7. Minimal Evidence Graph

V1 deliberately does **not** build a full market digital twin.

Allowed node classes:
- `candidate`
- `claim`
- `evidence`
- `assumption`
- `rule`
- `experiment`
- `failure_pattern`

Allowed edge classes:
- `supports`
- `contradicts`
- `depends_on`
- `tested_by`
- `invalidated_by`
- `supersedes`
- `derived_from`

Every evidence-bearing node preserves source, retrieval time, content/hash reference, point-in-time status and producer/method.

The graph is a dependency/provenance layer, not a truth oracle.

## 8. Failure Memory

Known research failure modes are represented as reusable machine-readable patterns.

Before expensive specialist work, each new candidate is checked against applicable known patterns. A match is not automatically a kill; it creates a required falsification question or fail-closed gate.

Examples include:
- same title but different contract semantics;
- settlement-source mismatch;
- theoretical identity without executable economics;
- UI/midpoint/last trade mistaken for executable price;
- score/state crossing mistaken for finality;
- gross edge erased by fees/depth/slippage/legging;
- lookahead or later-revision leakage;
- adaptive search/multiple testing;
- inactive rewards or changed fee regime;
- stale mirrors and stale books;
- hidden exception classes;
- shared upstream source masquerading as independent confirmation.

## 9. Scheduler policy

The scheduler does not estimate fake decimal probabilities for research value.

Each eligible task receives ordinal assessments for:
- decision relevance;
- uncertainty reduction;
- novelty;
- time sensitivity;
- dependency unlock value;
- evidence cost;
- model cost;
- duplication risk.

Scheduling rule:

> Prefer the cheapest admissible task that can change a decisive gate or unblock multiple downstream tasks, while preserving protected exploration capacity.

Tie breakers:
1. fail-closed semantic/source checks before strategy engineering;
2. tests capable of killing a route cheaply before expensive evidence collection;
3. point-in-time/execution evidence before additional narrative support;
4. tasks that unlock multiple blocked tasks;
5. older plausible candidates only after the above.

No-starvation:
- Discovery always receives protected capacity during an ACTIVE-HOUR.
- Plausible candidates with unresolved decisive questions remain schedulable.
- `WAITING_FOR_DATA` candidates do not monopolize AI capacity.
- 10–20% of discovery capacity remains exploration-oriented unless time-critical evidence justifies a temporary override that is recorded.

## 10. Hypothesis accounting

Every search family records:
- family ID;
- hypotheses examined;
- parameterizations/subgroups examined;
- data periods seen;
- post-hoc mutations;
- failed variants;
- surviving variants;
- untouched evidence remaining.

A survivor discovered after broad adaptive search cannot be presented as equivalent to a preregistered first-shot hypothesis.

## 11. Red Team independence

Red Team receives the claim, raw evidence references, rules, data, assumptions and required gates. It should not receive persuasive thesis prose, confidence language or the original worker's expected result when avoidable.

Attack order:
1. semantic/source attack;
2. timestamp/lookahead/revision attack;
3. mechanism/logical counterexample attack;
4. statistical/multiple-testing attack;
5. market/execution/friction attack;
6. regime/robustness attack;
7. methodology/process attack.

Red Team may recommend `KILL`, `PARK`, `NEEDS_EVIDENCE` or `SURVIVED_RED_TEAM`. It cannot promote an economic edge on its own.

## 12. Independent reproduction

A temporary reproducer is spawned only when a candidate has enough evidence that independent duplication can change a promotion gate.

The reproducer receives the preregistered question, necessary raw evidence/data and rules, but not the originating worker's reasoning path or conclusion where technically possible.

A result is not independent if both implementations unknowingly depend on the same upstream derived dataset/source. Source independence is recorded explicitly.

## 13. Promotion logic

V1 distinguishes paths that do and do not need a predictive signal.

Possible route A:
`mechanism -> signal -> market -> execution -> validation -> holdout -> reproduction -> shadow`

Possible route B (e.g. payout identity):
`mechanism -> market -> execution -> validation -> holdout/replay as applicable -> reproduction -> shadow`

`signal` may be `N/A` only when the mechanism does not depend on forecasting an uncertain outcome.

Promotion is deterministic from required gates. Director coordinates the procedure but cannot waive a failed required gate.

## 14. Resurrection

`KILL` is never deletion.

Every kill should name the decisive condition when possible. If fresh point-in-time evidence changes that condition, the candidate may return to `WATCH`/`NEEDS_FALSIFICATION` with an `EDGE_RESURRECTION` event.

A resurrected candidate does not inherit old validation as if the new regime had already been tested.

## 15. Source coverage

Scout performance is not measured by raw source count or keyword hits alone.

Track at minimum:
- source families attempted;
- successful retrievals;
- changed/new documents;
- primary-source ratio;
- duplicate-source ratio between scouts;
- unique relevant evidence items;
- unsupported community leads;
- explicit coverage gaps;
- stale/failed sources.

The bounded hourly source registry is a probe universe, not proof that discovery coverage is complete.

## 16. Plus-native execution hypothesis

Current runtime is a single ChatGPT-turn transport. V1 will therefore be shadow-tested before assuming true model parallelism.

For a no-API Plus deployment, the working hypothesis is a five-slot orchestration model:
1. Primary Scout;
2. Recon Scout;
3. Specialist Dispatcher/Worker;
4. Red Team/Reproducer slot;
5. Director/Consolidator.

This is **not yet an implementation claim**. Native Scheduled Task app access, GitHub read/write behavior, scheduling overlap, duplicate delivery and context isolation must pass a canary before the topology is trusted.

## 17. V1 non-goals

Do not build in V1:
- a complete venue digital twin;
- self-modifying evidence standards;
- autonomous methodology changes without review;
- unlimited agent-to-agent chat/debate;
- permanent independent workers for every old role;
- an optimizer that assigns fabricated probability-of-success values;
- paid model/API infrastructure;
- live execution or wallet automation;
- a strategy code build solely because an LLM finds an idea interesting.

## 18. Shadow acceptance criteria

Research OS V1 may replace the current control plane only if a preregistered shadow benchmark shows that it improves evidence efficiency without increasing false-survivor or premature-kill risk.

Primary benchmark dimensions:
- unique relevant evidence per model-worker run;
- duplicate research ratio;
- steps to decisive falsification;
- known failure patterns detected before expensive work;
- survivor preservation;
- contradiction discovery;
- point-in-time/provenance completeness;
- independent-source coverage;
- queue starvation;
- coordinator overhead;
- usage consumption where observable.

A prettier architecture, more agent activity or more generated text is not success.

## 19. Current design decision

**Build target:** six responsibility domains over a deterministic Governor, a central Director, protected dual discovery, an elastic specialist pool, minimal Evidence Graph, Failure Memory, hypothesis accounting and conditional blind reproduction.

**Runtime target:** smallest useful concurrency; normally 3–5 workers when parallelism justifies it.

**Economic conclusion:** `NO_PROVEN_EDGE`.
