# Polymarket hourly findings — 2026-09-20 22:00 CEST

Status: RESEARCH_ONLY / NO_PROVEN_EDGE

## PM-NR-AUGMENTED-004 — augmented NegRisk requires time-versioned outcome semantics

Fresh primary-source evidence from Polymarket's official `agent-skills` repository adds a material semantic guardrail to the NegRisk lane.

The official CTF operations reference distinguishes ordinary Negative Risk from **Augmented Negative Risk**. Augmented events may contain named outcomes, placeholder outcomes that are clarified after trading begins, and an explicit `Other` outcome. The reference says to trade only named outcomes, ignore placeholders, and warns that the definition of `Other` changes as placeholders are clarified. It also identifies augmented events through `enableNegRisk: true` plus `negRiskAugmented: true`.

Primary source: https://github.com/Polymarket/agent-skills/blob/main/ctf-operations.md (retrieved 2026-09-20).

## Consequence for Market Algebra

A NegRisk event cannot be treated as a static outcome partition merely because `negRisk=true`.

For every conversion/equivalence proof, the semantic state must now include at least:

- ordinary versus augmented NegRisk;
- the point-in-time set of named outcomes;
- placeholder identities/status at that timestamp;
- the point-in-time meaning of `Other`;
- exact-one-TRUE / resolution rules for that event version;
- identifier provenance and the CLOB token set corresponding to the same semantic version.

A conversion portfolio that is algebraically valid against today's labels may not be a valid point-in-time replay if placeholders or `Other` had a different meaning at the historical observation time. This is a leakage/version-drift risk, not an economic edge.

## Additional primary-source confirmation

The same official Polymarket repository states that Gamma, Data API and CLOB read endpoints are public/no-auth for data retrieval, and documents public market WebSocket access. This supports the zero-cost research path already identified at 21:00, but is not counted as a new economic finding.

## Falsification impact

Pre-Build Killer: PASS only as a semantic/data-model correction; FAIL as strategy warrant.

Chief Falsifier:

1. Semantic: reject any NegRisk proof that fails to classify augmented status and version outcome labels.
2. Point-in-time: historical replay must preserve contemporaneous placeholder/Other semantics; current Gamma metadata cannot backfill them silently.
3. Execution: even a semantically valid conversion still requires synchronized full depth, conversion fee, gas/approvals/inventory and output-depth proof.

Independent reproduction is not triggered because no positive economic instance exists.

Decision: KEEP RESEARCHING `PM-NR-V2-CONVERT-001`; `NO_PROVEN_EDGE`.
