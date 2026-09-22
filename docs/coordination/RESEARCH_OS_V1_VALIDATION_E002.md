# Research OS V1 — validation snapshot E002

Status: **VALIDATION QUEUED / DO NOT MERGE / SHADOW ONLY**

Frozen semantic source: `cea418468606b4bbe77f20861c55f1d0bd7732a3`

Validation branch: `ai/research-os-v1-frozen-validation`

Validation snapshot head: `c0716bfbe6299d1fddbca2bb8f0bf4c872dd127a`

Snapshot construction: current `main` at `12f777020a977f9010cfe0743727ed72a9372206` plus only the frozen Research-OS sidecar/tests/benchmarks/docs from the semantic freeze.

Git compare at snapshot creation: **ahead 1 / behind 0** versus that `main`; changed paths were confined to:

- `control/research_os_v1/*`
- `tests/research_os_v1/*`
- `benchmarks/research_os_v1/*`
- `docs/RESEARCH_OS_V1_*`
- `docs/PLUS_NATIVE_RESEARCH_OS_CANARY.md`

No active hourly, bridge, executor, Weather or Recon runtime file was replaced by the snapshot.

Local validator wrapper: `control/jobs/validate_research_os_frozen_e002.py`

Queued task: `RESEARCH-OS-V1-FROZEN-VALIDATE-E002`

Required validation behavior:

1. detached temporary worktree only;
2. credentials stripped from subprocess environment;
3. Research OS tests;
4. prebuild validator;
5. schema-alignment validator;
6. runtime validator;
7. full repository regression tests;
8. real read-only `shadow_cli` against committed candidate/agent-packet inputs;
9. tracked working tree must remain clean;
10. economic conclusion remains `NO_PROVEN_EDGE`.

Until E002 produces a committed PASS result, Research OS V1 remains **NOT LOCALLY VALIDATED** and PR #21 remains draft/shadow-only.

No paid API/model fallback, live trading, wallet/fund movement, credential export, merge or activation is authorized by this file.
