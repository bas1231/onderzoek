# Research OS V1 — coordination marker

Status: **HARDENING FROZEN / SHADOW VALIDATION ONLY / DO NOT MERGE YET**

Owner lane: Research OS V1 architecture consolidation

Design branch: `ai/research-os-v1-prebuild-spec`

Primary integration branch: `ai/research-os-v1-integration-shadow`

Hardening-freeze head: `cea418468606b4bbe77f20861c55f1d0bd7732a3`

Primary draft PR: **#21**

Canonical active runtime remains: `main`

## Current coordination state — 2026-09-22

Research OS V1 static/adversarial hardening is **content-frozen before final reconciliation and execution testing**. Other sessions may continue normal Weather, Recon, bridge, executor and hourly work on `main`.

At the freeze comparison the Research OS branch was **112 commits ahead / 76 commits behind `main`**, while every changed path remained confined to Research-OS sidecar/docs/tests/benchmarks. No active `control/hourly/*`, Weather, Recon, bridge or executor runtime file is part of the Research OS diff.

The branch will not be continuously rebased while unrelated sessions continue moving `main`. The next structural change is one deliberate final reconciliation against the then-current `main`.

### Merge decision

**NO MERGE NOW. PR #21 remains draft/shadow-only.**

Required sequence: preserve freeze → one final reconcile → newest tested `main` wins on overlap → local/free Research OS tests and validators → full current regressions → real read-only shadow run → preregistered unseen A/B shadow benchmark → only then review the smallest possible active-factory hook. Merge/activation remains a separate deliberate step and is never automatically authorized by benchmark PASS.

## Frozen hardening invariants

The freeze includes:

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
- FAILED/NO_NEW_EVIDENCE results cannot carry a positive economic state;
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
- benchmark baseline/challenger require identical unique case IDs and frozen case metadata;
- missing/zero benchmark denominators are UNKNOWN;
- malformed benchmark values fail closed;
- Plus task-slot observations are capacity snapshots, not scientific invariants.

All benchmark/methodology hardening was frozen **before the first unseen Research OS shadow dataset is accepted**.

## Six responsibility domains

1. Discovery
2. Market Research
3. Mechanics
4. Algebra
5. Red Team / Pentest
6. Research Director

Independent Reproduction remains a temporary isolated validation step rather than a permanent seventh role.

## Owned paths

- `control/research_os_v1/*`
- `benchmarks/research_os_v1/*`
- `docs/RESEARCH_OS_V1_*`
- `docs/PLUS_NATIVE_RESEARCH_OS_CANARY.md`
- `tests/research_os_v1/*`

## Rules for other sessions

1. **Do not merge PR #21 into `main` yet.**
2. Continue normal Weather, Recon, bridge, executor and hourly work on `main`.
3. Do not add semantic Research-OS hardening after freeze without recording the reason/conflict in Git first.
4. Do not create a competing `control/research_os_v1/*` implementation on `main`.
5. New `main` behavior is an input to final reconcile; newest tested runtime behavior wins.
6. Preserve `NO_PROVEN_EDGE`, point-in-time, provenance, negative evidence, holdout, no-post-hoc-relaxation and execution-realistic gates.
7. No paid API/model calls, live trading, wallet/fund movement or hidden cost paths.
8. On semantic conflict: document + fail closed, never silently choose.

## Final validation gate

Before PR #21 can leave draft:

1. final reconcile against latest `main`;
2. `pytest -q tests/research_os_v1` locally/free;
3. `python -m control.research_os_v1.validate_prebuild_spec`;
4. `python -m control.research_os_v1.validate_schema_alignment`;
5. `python -m control.research_os_v1.validate_runtime`;
6. full current hourly/bridge/Recon/Weather regressions;
7. real read-only `shadow_cli` run;
8. ≥20 unseen candidate-events / ≥10 ACTIVE-HOUR cycles on identical preregistered baseline/challenger cases;
9. no hard-fail condition and no regression in survivor preservation, false-survivor control or provenance completeness;
10. separate review of any active-factory hook after scientific acceptance.

No automatic activation is authorized by this coordination file.

Economic default remains: `NO_PROVEN_EDGE`.
