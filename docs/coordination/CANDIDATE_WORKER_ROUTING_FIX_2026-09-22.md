# Coordination — Candidate → Worker Routing Fix

Date: 2026-09-22
Status: ACTIVE
Priority: P0 infrastructure/research orchestration

## Problem

The Research-OS candidate queue contains non-terminal candidates, but primary agent work-items are emitted with empty `candidate_ids`.

Observed candidates include:
- `KWI-INCOMPLETE-TO-CANONICAL-V1`
- `PAYOFF-IDENTITY-MINING-V1`
- `ASSET-RANK-MAKER-HEDGE-V1`
- `KWI-FULL-STATION-PRECANONICAL-V1`

Observed symptom in 11:00 flow: candidate queue is populated, while all seven AI work-items carry `candidate_ids: []`.

Root-cause hypothesis confirmed by code inspection: `control/hourly/agent_orchestrator.py` decides readiness for `PRIMARY_ROLES` based on routed evidence (`has_evidence(packet)`), but there is no candidate-queue → primary-packet hydration step before orchestration. `has_candidate()` is only used by `prebuild_killer`, so queued candidates can remain visible yet never be assigned to primary workers.

## Ownership split

### Session A — E2E acceptance / independent reviewer
Owner: current ChatGPT session with Leon.

Responsibilities:
1. Do NOT modify candidate-routing implementation files while Session B is working.
2. Verify the 10:00 AI response is automatically ingested by the next Strix cycle and produces receipt/status evidence.
3. Review Session B's commit/diff/tests independently after publication.
4. Verify a post-fix canary run proves real candidate IDs reach the intended primary workers and survive through AI request/response processing.
5. Fail closed on ambiguity. No live trading, paid actions, wallet actions, or OpenAI API costs.

### Session B — implementation owner
Responsibilities:
1. Own the candidate → worker routing repair.
2. Work from the latest `main`; avoid editing unrelated files.
3. Implement deterministic candidate hydration/routing before primary agent packets are finalized.
4. Preserve current safety and validation semantics; do not weaken Pre-Build Killer, Chief Falsifier, Independent Reproducer, WATCH/HUNT separation, or `NO_PROVEN_EDGE` default.
5. Add focused tests and run the relevant full hourly test suite plus compile checks.
6. Commit/push only the routing fix and tests. Do not deploy live trading or cost-bearing actions.
7. Publish changed files, test output, commit SHA, and any remaining limitation in Git or chat.

## Required routing semantics

The fix must NOT blindly attach every candidate to every worker.

Candidate assignment must be deterministic and explainable from candidate metadata / mechanism / phase / next decisive test / required data / role responsibility. At minimum:
- weather/KWI candidates route to `weather_twc` and, when source/finality is material, `settlement`;
- payoff-identity candidates route to `algebra` and, when executable economics are material, `microstructure`/`settlement` as justified;
- maker/hedge/execution candidates route to `microstructure` and relevant specialist roles as justified;
- `scout`/`recon_scout` may receive a candidate only when the unresolved question is discovery/recon rather than specialist proof;
- `research_director` must retain queue visibility but should not be used as a substitute for missing specialist assignment.

A candidate may route to more than one role only where responsibilities genuinely overlap. Every assignment must be traceable in the packet or orchestration summary with a reason.

## Acceptance criteria

A. Unit tests
- A non-terminal candidate with a weather/TWC decisive question is hydrated into the appropriate primary worker packet.
- A payoff-identity candidate is hydrated into algebra and not indiscriminately into unrelated roles.
- Candidate routing is deterministic and deduplicated.
- Existing routed-evidence-only behavior still works.
- Empty/no candidate queue still behaves safely.
- Terminal/parked candidates are not incorrectly reactivated.
- Safety flags remain false.

B. Regression
- Existing `tests/hourly/test_agent_orchestrator.py` remains green.
- Relevant hourly/orchestrator test suite remains green.
- `python -m compileall` (or project-standard compile gate) passes.

C. Integration canary
Generate one fresh research run with the four current non-terminal candidates and prove:
1. queue contains the candidates;
2. at least the intended primary work-items have non-empty `candidate_ids`;
3. unrelated workers do not receive them without a routing reason;
4. AI work bundle preserves those candidate IDs;
5. AI response echoes/acts on those candidate IDs where requested;
6. Director can make a candidate-specific next-step decision;
7. no promotion/negative-close is manufactured merely because routing exists.

## Coordination rule

Session B owns implementation files for this fix until it publishes a commit SHA. Session A remains read-only on those files and handles E2E acceptance/review. If Session B discovers a broader architectural change is required, record it here or in a new coordination note before expanding scope.

## Safety

Research only. `live_trading=false`, `paid_actions=false`, `wallet_actions=false`, `openai_api=false`. No wallet/fund movement, paid service/API, live order, or credentials change.
