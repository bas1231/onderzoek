# Research OS V1 — coordination marker

Status: **E004 CORE PASS / PROSPECTIVE SHADOW COLLECTION BUILD / DO NOT MERGE OR ACTIVATE YET**

Owner lane: Research OS V1 architecture consolidation

Primary integration branch: `ai/research-os-v1-integration-shadow`

Prospective collection branch: `ai/research-os-v1-shadow-collection`

Validated E004 snapshot: `a525682ea32e8d46cfb79b6e3f1ab059bcadab4f`

Current collection head at this marker: `d1bb57ca7e521538d259338623f5fca37624c2d6`

Primary draft PR: **#21**

Canonical active runtime remains: `main`

## Current coordination state — 2026-09-22

Research OS V1 core/hardening has now passed the isolated E004 validation on the local Strix environment:

- `159/159` Research OS tests PASS;
- `338/338` full repository tests PASS;
- prebuild validator PASS;
- runtime validator PASS;
- schema-alignment validator PASS;
- real committed agent-packet discovery PASS;
- real read-only `shadow_cli` PASS;
- tracked mutation check PASS;
- `live_trading=false`, `paid_actions=false`, `wallet_actions=false`, `runtime_mutation=false`, `main_mutation=false`;
- economic conclusion remained `NO_PROVEN_EDGE`;
- E004 exit code `0`.

The E004-tested core remains the reference. New prospective benchmark/collection engineering is isolated on `ai/research-os-v1-shadow-collection`, which started from that exact E004 snapshot. Do not interpret new collector code as having inherited E004 PASS; it requires its own local validation before datapoint 1.

### Main instrumentation-only change

`main` contains one intentional Research-OS-related active-file change: `control/hourly/scheduled_worker_contract.json` now carries `prospective_shadow_telemetry` instructions. This is **instrumentation only**:

- no extra Scheduled Task;
- no schedule/cadence increase;
- no additional paid/model/API worker;
- no candidate promotion/kill authority change;
- no live/paid/wallet capability change;
- no runtime strategy/execution change;
- native runs without a valid paired exchange request/response are not accepted as prospective benchmark cases.

The four existing staggered Prediction tasks remain the research execution budget. The telemetry extension is intended to make their existing `ai/runtime-exchange` role results measurable without purchasing or creating a second challenger run.

## Prospective benchmark design — frozen before datapoint 1

The prospective collection branch now defines the benchmark path:

`paired ai/runtime-exchange request+response → immutable exchange bundle/cycle → raw baseline/challenger telemetry → automatic cohort cutoff → deterministic ground-truth resolver → exact materialization → structured metric derivation → paired M1–M12 comparison → preregistered scientific replacement gate`.

Key frozen rules:

1. One case is one canonical candidate in one ACTIVE-HOUR; no agent-count multiplication.
2. Eligible input is a valid point-in-time `PVA_AI_EXCHANGE_REQUEST_V1` paired with its exact `PVA_AI_EXCHANGE_RESPONSE_V1` by run ID/request hash/token.
3. Case identity and representative task are chosen from the pre-response request, never from later findings.
4. Ground truth starts `UNRESOLVED` and is assigned only by the deterministic later resolver.
5. The automatic cohort freezes at the first cycle where at least 20 candidate-events, 10 ACTIVE-HOUR cycles and 2 task-shapes are present.
6. Later cycles may resolve frozen cases but may not add/replace benchmark cases.
7. Unresolved cohort cases block the replacement gate rather than being dropped.
8. The cohort requires at least one `SURVIVOR` and one `DECISIVE_NEGATIVE`; otherwise it becomes `INSUFFICIENT_CLASS_BALANCE`.
9. `DECISIVE_NEGATIVE` takes precedence over survivor classification.
10. Mere age/repeated presence is not a survivor signal; survivor requires at least three later cycles plus substantive progress/wait state.
11. Baseline and challenger must contain the identical frozen case set and metadata.
12. Benchmark metrics are derived from structured underlying worker/evidence/research/failure telemetry; self-reported aggregate counts are ignored.
13. A challenger no-allocation is explicit, never a dropped case: zero role work + `KEEP`; a later negative therefore becomes a false survivor.
14. Transport self-references may be retained for provenance but cannot count as relevant evidence.
15. The logical challenger is frozen to LOW_USAGE replay: protected Scout + Recon, at most one scheduler-selected dynamic Specialist/Red-Team/Reproducer role, and Director; max four logical role units inside the existing scheduled model turn.
16. Logical role units are not represented as independent AI/model invocations; actual task/model usage remains separate.
17. The challenger can only select roles that the legacy pre-response request already exposed; it cannot invent later work/evidence.
18. No extra scheduled AI/model turn is required for the benchmark.
19. Even a scientific replacement PASS never authorizes runtime replacement automatically; a separate human integration decision remains mandatory.
20. Economic default remains `NO_PROVEN_EDGE`.

## Merge decision

**NO MERGE NOW. PR #21 remains draft/shadow-only. Do not merge the prospective collection branch either.**

Required sequence from here:

1. finish prospective collection/evaluation code on `ai/research-os-v1-shadow-collection` only;
2. create a latest-main + collection-sidecar validation snapshot;
3. run the full Research-OS prospective tests/validators locally/free;
4. run the complete repository regression suite against that snapshot;
5. accept datapoint 1 only after those tests pass;
6. collect the frozen prospective cohort through existing scheduled/exchange traffic, without extra paid/model cadence;
7. evaluate the preregistered paired benchmark;
8. only if the scientific gate passes, design/review the smallest active runtime hook;
9. merge/activation remains a separate explicit decision.

## Frozen core hardening invariants

The validated core includes:

- deterministic Governor; unknown/paid/live/wallet actions fail closed or require specific user approval;
- unknown/non-ready legacy states cannot silently become READY;
- duplicate task/candidate IDs fail closed;
- canonical candidate state is type-strict; unknown queue status/priority fails closed;
- conflicting legacy `gates` vs canonical `required_gates` fails closed;
- partial legacy gate labels never upgrade to PASS;
- Evidence Graph evidence nodes require provenance plus explicit point-in-time status;
- Evidence Graph rejects self-edges and simultaneous supports/contradicts polarity for the same pair;
- worker results are task-aware: worker/task/candidate identity must match;
- Discovery and Red Team cannot emit positive economic conclusions;
- failed/no-new-evidence results cannot carry a positive economic state;
- PASS/FAIL gate effects require basis refs that actually exist in task inputs/result evidence;
- holdout is mandatory for promotion;
- every present/future required gate is binding;
- no-signal route requires explicit `signal_edge=NOT_APPLICABLE`;
- Primary/Recon coverage requires explicit successful retrieval; missing retrieval status is UNKNOWN;
- unidentified sources cannot inflate proven-unique evidence counts;
- Reproducer checks artifact hash/source identity plus explicit upstream lineage before independence can PASS;
- Red Team and Reproducer are blind to origin gate outcomes and supporting-vs-contradictory evidence polarity;
- resurrection resets legacy+canonical gate union to PENDING and keeps old states only in history;
- Failure Memory pattern hit creates a required check and never auto-kills by pattern match alone;
- zero/missing search-family trials cannot masquerade as a clean preregistered path;
- resolved variants cannot exceed the registered search universe;
- missing/malformed benchmark evidence fails closed;
- Plus task-slot observations are capacity snapshots, not scientific invariants.

## Owned paths

Core/collection lane owns:

- `control/research_os_v1/*`
- `benchmarks/research_os_v1/*`
- `docs/RESEARCH_OS_V1_*`
- `docs/PLUS_NATIVE_RESEARCH_OS_CANARY.md`
- `tests/research_os_v1/*`

Other sessions may continue normal Weather, Recon, bridge, executor and hourly work on `main`. Do not start a second competing prospective Research-OS collector/benchmark implementation. If an active-main behavior conflicts with the shadow design, document the conflict and preserve the newer tested main behavior for reconciliation.

## Safety

No paid API/model calls, live trading/orders, wallet/fund movement, credential export or hidden cost paths are authorized. No scientific benchmark result authorizes those actions.

Economic default remains: `NO_PROVEN_EDGE`.
