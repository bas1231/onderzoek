# Prediction model execution routing

Status: NORMATIVE TARGET — BUILD REQUIRED
Updated: 2026-10-07

## Canonical routing

- SOL_PROPOSAL -> DIRECT_SOL -> exact GPT-5.6 Sol
- SOL_BUILD -> DIRECT_SOL -> exact GPT-5.6 Sol
- ASTRA_PREBUILD -> CODEX_WORKER -> exact GPT-6 Astra
- ASTRA_POSTBUILD -> CODEX_WORKER -> exact GPT-6 Astra
- Astra supervisor review -> CODEX_WORKER -> exact GPT-6 Astra

Canonical shorthand: **Sol direct; Astra via Codex**.

Sol must not depend on Codex quota. The direct Sol path uses the already-connected ChatGPT-plan direct-inference capability through a bounded loopback-only broker. Prediction receives only model output plus provenance and does not own the authentication layer.

The direct route must enforce exact model slug `gpt-5.6-sol`, `store=false`, no tools/actions, immutable prompt hashing, exact completion provenance, idempotent completed tasks and fail-closed handling of wrong model or malformed output.

Astra remains deliberately on CodexWorker as the independent reviewer.

The scientific lifecycle remains unchanged:

`Scout -> selectie -> Sol-opzet -> Astra PREBUILD -> Sol-build -> Astra POSTBUILD -> tests/meting -> supervisor -> rapportage`

Hard invariant remains:

`NO_TEST_OR_MEASUREMENT_BEFORE_ASTRA_POSTBUILD_APPROVAL`.

## Active R4 migration

The incomplete Codex-backed `A2Z-V4-SOL-BUILD-20261007-R4` run stopped because of the Codex execution-layer usage limit. This is not a scientific rejection by Sol.

Preserve the R4 prompt/binding and Astra R3-P2 feedback. Execute that governed R4 content through DIRECT_SOL with fresh provenance. The resulting build must receive a fresh exact GPT-6 Astra POSTBUILD review before any substantive tests or measurements.

Until runtime tests pass:

`DIRECT_SOL_STATUS = NOT_YET_PROVEN`
`scientific_status = NO_PROVEN_EDGE`
