# WS-CROSSVENUE-COMPARISON-001 — Prediction.com cross-venue comparison layer

- observed_at: 2026-09-19T17:58:44+02:00
- source_class: PRIMARY_VENDOR_ANNOUNCEMENT
- status: FACT_VERIFIED / WEAK_SIGNAL
- venues: multi-venue prediction markets
- mechanism_id: MECH-CROSSVENUE-COMPARISON-DISTRIBUTION
- provenance: Genius Sports press release, 2026-09-17
- primary_source: https://www.geniussports.com/newsroom/genius-sports-launches-prediction-com-the-premium-prediction-market-platform-for-comparing-probabilities-event-contracts-and-insights/

## Finding
Genius Sports launched Prediction.com, which explicitly compares equivalent event contracts across multiple prediction venues and includes a proprietary cross-venue multi-leg pricing engine. For sports it combines official/live Genius data with real-time prediction-market pricing.

## Why it matters
This independently validates that cross-venue semantic matching and multi-leg comparison are becoming an explicit product category, not merely an internal research idea. It also likely increases crowding/decay risk for simple visible cross-venue price discrepancies. Conversely, the public comparison layer can become a discovery/benchmark source for semantic-equivalence errors, venue-specific lag, and multi-leg discrepancies.

## Relation to known
Directly related to cashflow identity mining, cross-venue contract identity, MVE/combo comparison, and live sports state-lock work. It weakens the assumption that obvious cross-venue equivalence will remain uncrowded; it strengthens the value of machine-verifiable semantics, less-obvious synthetic identities, and execution-aware residuals.

## Transfer hypothesis
If a comparison product maps contracts imperfectly or exposes prices faster than retail tooling elsewhere, it may reveal candidate discrepancies; no edge is assumed. The more important benchmark is whether our theorem/proof layer can discover equivalences beyond the comparator's visible universe.

## Required data
- supported venues and market families
- timestamps/refresh cadence
- mapping methodology and multi-leg coverage
- executable L2 from underlying venues
- historical comparator snapshots if obtainable legally/publicly

## Falsification
Sample matched contracts and multi-leg combinations, independently prove payout equivalence, then compare Prediction.com-displayed gaps against executable underlying L2 after fees/slippage. Kill as an edge source if displayed gaps are stale/non-executable or disappear before realistic arrival.

## Execution blockers
Unknown refresh latency; displayed price may not be executable; semantic mapping errors; account/geographic constraints; fees and partial fills.

## Weak-signal score (0-5)
- novelty: 4
- source_strength: 5
- mechanism_distance_from_known: 2
- plausible_economic_impact: 4
- transferability: 5
- time_sensitivity: 4
- testability: 4
- data_availability: 3
- legality: 5
- tail_upside: 3
- rarity: 3
- opportunity_lifetime: 3
- capital_scalability: 3

## Reason now
Launched 2026-09-17. This is time-sensitive mainly because it may accelerate crowding in straightforward cross-venue comparison and provides a new benchmark/discovery surface now.

NO_PROVEN_EDGE.