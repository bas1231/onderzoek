# Kalshi first/stable decidability paper — 2026-09-19

Status: **NEW_EXTERNAL_RESEARCH / MECHANISM_PLAUSIBLE / NO_PROVEN_EDGE**

## Source/provenance
- Maksym Nechepurenko, *From Public Evidence to Contractual Outcome: First and Stable Decidability on Kalshi*, arXiv:2609.16642, published 2026-09-15.
- Cross-check: SSRN version posted 2026-09-12.
- Research captured 2026-09-19.

## Mechanism
The paper formalizes two clocks that map directly onto Proof Hunter's pre-settlement lane:
1. **first decidability** — earliest contemporaneous time when the contract rules plus admissible public evidence imply exactly one settlement value and all required future conditions are complete;
2. **stable decidability** — retrospective earliest time after which that singleton never changes through finalization.

Potential economic mechanism: if first decidability occurs while the market remains executable and executable price has not converged to terminal value, a terminal-value gap may exist. This is a measurement target, not evidence of profit.

## Evidence level
**Methodological / prospective-infrastructure evidence, not trading-edge evidence.**

Reported results:
- frozen blind pilot: 25/25 identities and blinding checks passed;
- current rule text recovered for 25/25;
- exact or bounded historical rule versions recovered for 0/25;
- exact or bounded official source-release objects recovered for 0/25;
- larger historical recovery: 152,694 ordinary tickers, 11,530 exact event identities, 6,540 read-only official requests, but zero historically eligible events/tickers;
- prospective shakedown: 3 source programmes / 25 markets, 781,266 lifecycle frames integrity-revalidated, 22 closed lower-bounded reconnect receipts, no unresolved reconnect gap, no due-but-missed official release;
- price layer inactive; paper reports no contractual-decidability, price, P&L or cross-venue result.

## Relation to existing hypotheses
**Strong reinforcement / refinement, not a duplicate.**
- Reinforces Proof Hunter pre-settlement unconditional-floor/state-lock work.
- Strongly validates our rule-version + source-release provenance requirement.
- Explains why retrospective settlement-edge backtests are unsafe when historical rules/releases are unavailable.
- Suggests separating `FIRST_DECIDABLE` from `STABLE_DECIDABLE` rather than treating a single finality timestamp as sufficient.
- Compatible with Weather Index preregistration: contemporaneous config/rule/source capture is mandatory before any price test.

## Required data
Prospectively frozen market identity; exact contemporaneous series/market rules; official source hierarchy; exact source-release object and receipt timestamp; correction/revision history; market lifecycle; synchronized executable L2; fee provenance; reconnect/gap evidence.

## Falsification test
For a preregistered prospective sample, compute first-decidability without venue determination/final result leakage. Then test whether a non-zero interval exists before market close/determination and whether executable terminal-value gaps survive fees, depth, latency and stale-book rejection. Kill the economic hypothesis if decidability almost always follows last executable time or prices already converge before/at first decidability.

## Execution risks
Rule drift; corrections/revisions; unfinished contract conditions; clock mismatch; reconnect gaps; source publication vs receipt ambiguity; price convergence before evidence ingestion; thin depth; fees; partial fills.

## Classification
- Novelty: **NEW relative to current canonical KB**
- Type: settlement/contract logic + measurement framework
- Evidence: methodological/prospective infrastructure
- Economic status: **NO_PROVEN_EDGE**
