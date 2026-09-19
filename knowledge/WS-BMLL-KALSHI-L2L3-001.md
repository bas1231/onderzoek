# WS-BMLL-KALSHI-L2L3-001 — institutional historical Kalshi order-book dataset

- observed_at: 2026-09-19T17:58:44+02:00
- source_class: PRIMARY_DATA_VENDOR_ANNOUNCEMENT
- status: FACT_VERIFIED / RESEARCH_PRIORITY_SIGNAL
- venue: Kalshi
- mechanism_id: MECH-HISTORICAL-MICROSTRUCTURE-BENCHMARK
- provenance: BMLL announcement, 2026-09-17
- primary_source: https://www.bmlltech.com/news/press-releases-and-news/bmll-and-kalshi-partner-to-expand-institutional-access-to-prediction-market-data

## Finding
BMLL announced integration of Kalshi historical prediction-market data into its institutional platform. BMLL describes its platform as historical Level 3/2/1 data and says Kalshi data are normalized into the same schema used for CME Event Contracts. Delivery includes institutional research workflows; the stated use cases include macro/event-driven strategy research.

## Why benchmark-worthy
This materially changes the evidence frontier for ordinary strategies. Historical order-book data make realistic studies of maker/taker economics, queue/fill proxies, spreads, depth, markouts, event-release response, fee thresholds and cross-market microstructure substantially more feasible for institutions. It does not itself prove any strategy and access/cost may block us, but it is strong evidence that institutional backtesting/crowding is accelerating.

## Relation to known
Relevant to Surplus Maker, FLB conditional maker research, execution-first validation, fee-rounding/minimum-edge work, macro release timing, and the new crypto cross-representation lane. It raises the bar: claims based only on candle/trade data are weaker when high-fidelity order-book history exists somewhere in the ecosystem.

## Strategy benchmark implication
Simple passive market making or event-response strategies should be judged against order-book-aware backtests with realistic fills and markouts. Expected crowding/decay risk rises as normalized data become commercially accessible.

## Required data
- exact Kalshi history depth/date coverage
- whether L3/order events are included for all periods/markets
- timestamps and sequence fidelity
- commercial access/cost
- fee/rebate history and rule-version joins

## Falsification / cheap next step
Request or inspect public schema/sample documentation and determine whether accessible samples contain sufficient timestamps/order events for queue-aware replay. If only coarse snapshots/trades are actually available, downgrade the signal. Independently compare our recorder fields with BMLL's published schema.

## Execution blockers
Likely paid/institutional access; historical rules/fees still need point-in-time provenance; L3 availability must be confirmed specifically for Kalshi rather than inferred from BMLL's general platform description.

## Scores (0-5)
- novelty: 4
- source_strength: 5
- plausible_economic_impact: 4
- transferability: 4
- time_sensitivity: 3
- testability: 5
- data_availability: 2
- legality: 5
- evidence_strength: 5 for dataset existence, 0 for strategy profitability
- crowding_decay_risk: 4
- execution_requirements: high-fidelity historical book + fee/rule joins
- reproducibility: potentially high if data access obtained

NO_PROVEN_EDGE.