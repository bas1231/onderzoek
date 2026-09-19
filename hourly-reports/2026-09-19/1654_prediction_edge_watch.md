# Prediction Edge Watch — 2026-09-19 16:54 CEST

## Scope
Canonical KB: `bas1231/onderzoek`. Git reviewed first, then fresh public research. Deduplication performed against the recent canonical commits visible at run time.

## A. Meaningful new Git content from other agents/sessions

### Weather Index lane materially upgraded
Recent commits added a full Weather Index research stack: source-conflict record, active candidate, preregistered three-angle experiment, task queue, bootstrap corpus, and a pre-publication nowcast hypothesis.

Most important new mechanism: for Miami hourly Weather Index contracts, the hypothesis is no longer generic weather forecasting. It is a narrow **pre-publication reconstruction** test: prospectively ingest the five HF-ASOS members and current calibration/config, estimate the still-unpublished canonical point, and ask whether any 1–5 minute information window exists before last executable market time.

The canonical note records Miami members KMIA/KOPF/KFLL/KFXE/KPMP, an eligibility deadline of event minute +300 seconds, >=4-member / >=0.80-weight quorum, fallback semantics, and point-in-time config requirements. Economic status remains `NO_PROVEN_EDGE`.

Relation: this is a sharper successor to the older weather-runner/miscalibration lane because it targets deterministic source timing rather than broad forecast superiority. It also obeys the existing three-angle rule: semantics -> point-in-time signal -> executable L2.

### Behavioral-flow lane
A recent commit adds behavioral flow hypotheses. Treat these as complementary to the existing FLB/maker-surplus lane, not independent proof: maker status alone is not edge; category/price bucket/side/flow and post-fill markouts still need preregistered measurement.

### MVE/combo lane
Recent commits added scalar-robust nested-MVE dominance work and an execution-first MVE/RFQ sweep. This extends the existing cashflow-identity/Market Algebra lane. Priority remains formal payout dominance/equivalence first, executable pricing second; large ticker count is discovery surface, not edge evidence.

### Negative evidence preserved
The repo also records an MLB strikeout-ladder negative scan. This is retained as falsification evidence rather than deleted.

## B. New external research this run

### First/stable contractual decidability — NEW
Source: Maksym Nechepurenko, arXiv:2609.16642 (2026-09-15), cross-checked against SSRN.

Mechanism: distinguish **first decidability** (earliest contemporaneous rules+public evidence singleton after all unfinished conditions are satisfied) from **stable decidability** (retrospective earliest time that singleton remains unchanged through finalization). This provides a cleaner formal clock for Proof Hunter's pre-settlement/state-lock lane.

Evidence level: methodological/prospective infrastructure only. The paper reports a 25-market blind pilot, 152,694 ordinary tickers / 11,530 exact event identities in historical recovery, and a prospective shakedown with 781,266 lifecycle frames, but explicitly reports no price/P&L edge. Crucially, historical rule versions and exact official release objects were unrecoverable in the retrospective pilot, which independently supports our decision to require prospective point-in-time provenance.

Needed data: exact contemporaneous rules, source release object and receipt time, revisions, lifecycle, synchronized L2, fees, reconnect-gap evidence.

Falsification: compute first-decidability prospectively without venue-result leakage; kill the economic hypothesis if it normally occurs after last executable time or executable prices have already converged after fees/depth/latency.

Execution risks: rule/source drift, revisions, unfinished conditions, clock mismatch, reconnect gaps, price convergence, fees/depth/partial fills.

Relation: strong reinforcement/refinement of Proof Hunter Phase-10/pre-settlement floor and Weather Index provenance gates; not a duplicate of the existing state-lock candidate because it supplies a formal evidence clock and exposes why retrospective backtests can be invalid.

## External items checked but not promoted
- Kalshi/CESifo maker-taker FLB paper: already represented in canonical hypotheses; duplicate/background.
- Kalshi August 2026 calibration research: useful baseline but no new mechanism beyond existing calibration/FLB lanes.
- Recent regulatory/sports-volume news: relevant operational context but no new edge mechanism.
- Crypto-event-contract hedging paper: portfolio-risk application, not a demonstrated mispricing edge; not promoted.

## Changes written this run
- `knowledge/kalshi/KALSHI_FIRST_STABLE_DECIDABILITY_PAPER_2026-09-19.md`
- this hourly report

## Current priority implication
1. Continue Weather Index prospective source/config/L2 capture.
2. Add `FIRST_DECIDABLE` and `STABLE_DECIDABLE` as distinct research concepts to future Proof Hunter settlement-edge experiments; do not infer them from Kalshi determination time.
3. Keep MVE identity search execution-first and formally verified.
4. Keep behavioral maker/FLB work empirical; no generic maker deployment.

No hypothesis is promoted to proven edge in this run.
