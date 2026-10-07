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

Sol must not depend on Codex quota. The direct Sol path uses a regular ChatGPT **Chat** session running exact GPT-5.6 Sol. It must not use Codex, ChatGPT Work, or Sign in with ChatGPT plan-sharing inference, because those routes can consume the Work/Codex allowance.

Canonical transport is `WSL governed request -> existing wake/session route -> GPT-5.6 Sol Chat worker -> GitHub connector completion -> WSL read-only import`. This reuses the existing bridge as transport; it does not authorize bridge mutation.

The direct route must preserve immutable prompt hashing, exact task/candidate/binding metadata, session-route attestation, completion provenance, idempotent completed tasks and fail-closed handling of wrong/missing worker attestation or malformed output. The Sol worker may use the GitHub connector only for the governed request/result records; it must not execute experiment code, tests, measurements, trades, paid actions or wallet actions.

Astra remains deliberately on CodexWorker as the independent reviewer.

The scientific lifecycle remains unchanged:

`Scout -> selectie -> Sol-opzet -> Astra PREBUILD -> Sol-build -> Astra POSTBUILD -> tests/meting -> supervisor -> rapportage`

Hard invariant remains:

`NO_TEST_OR_MEASUREMENT_BEFORE_ASTRA_POSTBUILD_APPROVAL`.

## Active R4 migration

The incomplete Codex-backed `A2Z-V4-SOL-BUILD-20261007-R4` run stopped because of the Codex execution-layer usage limit. This is not a scientific rejection by Sol.

Preserve the R4 prompt/binding and Astra R3-P2 feedback. Execute that governed R4 content through DIRECT_SOL with fresh provenance. The resulting build must receive a fresh exact GPT-6 Astra POSTBUILD review before any substantive tests or measurements.

Until runtime tests pass:

`DIRECT_SOL_CHAT_STATUS = NOT_YET_PROVEN`
`scientific_status = NO_PROVEN_EDGE`
