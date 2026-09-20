# Hourly durable finding — 2026-09-20 16:00 CEST

Status: RESEARCH_ONLY / NO_PROVEN_EDGE

## New finding — payoff identity is not enough; conversion direction is a first-class execution primitive

A recent paper, *Executable Arbitrage and Market Efficiency in Prediction Markets* (arXiv:2608.00666, Aug 2026), reconstructs depth-aware executable portfolio values for Polymarket negative-risk markets and separates terminal payoff no-arbitrage from protocol-executable no-arbitrage. Its key mechanism claim is that the NegRisk Adapter exposes only one pre-settlement conversion direction (NO-to-YES), so algebraically equivalent violations need not be symmetrically executable before settlement. The paper reports substantially fewer/shorter violations on the adapter-supported side and estimates most measured arbitrage profit through converter-enabled strategies rather than settlement-only basket formation.

Source: https://arxiv.org/abs/2608.00666

### Research consequence

For Market Algebra / cross-venue theorem proving, `Payout_A(s) == Payout_B(s)` remains necessary but is not sufficient for an executable edge. Every candidate must additionally carry an explicit **transformation graph**:

- which portfolio transformations/conversions the venue protocol actually exposes;
- directionality of each conversion;
- whether conversion is available pre-settlement or only at settlement;
- collateral release / capital lock-up implications;
- fees/gas/latency and depth on the acquisition legs;
- inventory requirements before a conversion can be invoked.

A proof whose profitable direction requires an unsupported reverse conversion is `PROTOCOL_EXECUTION_BLOCKED`, not an arbitrage candidate.

### Pre-Build Killer

- Novelty in repo search: no existing `2608.00666` or `NegRisk Adapter` record found before this write.
- Semantic/mechanism value: PASS as a research constraint.
- Economic headroom: NOT ESTABLISHED for a current candidate.
- Executable current opportunity: NOT TESTED / no synchronized L2 portfolio evidence in this run.
- Independent reproduction: ABSENT.

Decision: keep as durable methodology/evidence; do not build strategy code and do not promote an economic candidate.

## Rejected/duplicate leads this hour

- ForecastEx public CSV: already recorded in the 15:00 run; no new execution evidence.
- Polymarket public-feed trade-direction problem: already recorded in the 15:00 run; not new.
- Generic cross-venue midpoint arbitrage pages: rejected as executable proof because midpoint snapshots do not establish simultaneous asks/depth, fees, or exact settlement identity.
- Settlement-manipulation literature: not promoted into an operational strategy; manipulation of settlement/underlying is outside the permitted research/execution boundary.

## Economic conclusion

`NO_PROVEN_EDGE`.
