# Fidonis resolution-integrity dataset — 2026-09-21

Status: **FACT_VERIFIED_AS_PUBLIC_DATA_SOURCE / RESEARCH_INPUT_ONLY / NO_PROVEN_EDGE**

## Finding

Fidonis publishes a free/public, reproducible resolution-integrity series for Polymarket UMA-resolved markets. It measures settlement disputes rather than forecast calibration. The public methodology defines a market as disputed iff its UMA resolution timeline contains a `disputed` state; it reports count dispute rate and volume-weighted dispute rate over traded markets with UMA resolution.

Current public headline observed 2026-09-21: 2,107 contested resolutions in the record and about $3.3244B of traded volume associated with markets that went to dispute. These are source-reported aggregates and are **not independently reproduced in this run**.

## Provenance / method

Source: https://fidonis.org/ and https://fidonis.org/methodology/ (retrieved 2026-09-21).

The documented lineage uses Polymarket Gamma `umaResolutionStatuses` for the dispute timeline, joined to a chain-validated resolution map and traded volume. Adapter-to-oracle topology is verified on-chain; individual `DisputePrice` log matching is explicitly described as a bounded sample rather than exhaustive. The series starts 2025-03, excludes trailing incomplete months with a three-month buffer, and publishes an append-only reproduction pack / methodology.

The source also reports a preregistered listing-time wording-model test (train 2025-03..2025-12; test 2026-01..2026-04) that failed to beat simple dispute base rates. Treat this as negative evidence against assuming that question-text modelling alone predicts dispute risk.

## Role routing

- `settlement`: HIGH relevance. Candidate input for empirical dispute/finality/capital-lock risk priors.
- `microstructure`: MEDIUM relevance only through settlement-delay/capital-lock costs; no bid/ask or fill evidence.
- `algebra`: MEDIUM relevance as a risk haircut for nominal payout identities that cross resolution/finality states.
- `scout`: source should be watched for new public editions/method changes.
- `behavioral`, `informed_flow`, `weather_twc`: no direct edge evidence in this finding.

## Pre-Build Killer

PASS only as a **research data source**. FAIL as a strategy candidate: no executable price discrepancy, no causal trading rule, no contemporaneous L2, no fee/depth/fill evidence.

## Chief Falsifier

Open failure modes before quantitative use:

1. Gamma status history is a venue REST input and may have coverage/version semantics that need spot reproduction.
2. Full-history dispute-log matching is not exhaustive according to the source itself.
3. Category/size base rates can be nonstationary and are not automatically transferable to future markets.
4. Dispute probability is not equivalent to expected economic loss; delay, final outcome changes, bond mechanics and capital cost must be modelled separately.

Independent Reproducer: **not activated**; no economic survivor is claimed.

## Economic interpretation

Signal edge: **NONE CLAIMED**.
Market edge: **NONE CLAIMED**.
Execution edge: **NONE CLAIMED**.

Useful consequence: settlement/finality risk can potentially be assigned empirical priors rather than a generic qualitative buffer, but only after independent reproduction and mapping to the exact market/oracle adapter/time regime.

**NO_PROVEN_EDGE**.
