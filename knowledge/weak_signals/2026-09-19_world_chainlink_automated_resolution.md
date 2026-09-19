# WS-ORACLE-003 — World ships feed-driven automated event resolution on Solana

- observed_at: 2026-09-19T17:53:00+02:00
- source_class: ECOSYSTEM_PRIMARY_ADJACENT + MULTIPLE_SECONDARY_CONFIRMATIONS
- provenance: Chainlink ecosystem publication 2026-09-14; World launch reporting 2026-09-09/11; independent launch coverage
- venues: World (Solana/Phantom); transfer relevance to Polymarket, Jupiter and other oracle-resolved venues
- mechanism_id: MECH-FEED-DRIVEN-RESOLUTION
- status: FACT_VERIFIED for launch/infrastructure; WEAK_SIGNAL for economic consequence; NO_PROVEN_EDGE

## Finding
World opened its standalone Solana prediction-market interface on 2026-09-09 after previously operating inside Phantom. Public launch material says World uses Chainlink Data Streams plus the Chainlink Runtime Environment (CRE) for high-speed data and automated/immediate market resolution, with CASH as settlement asset. Reporting describes this as a design that reduces or removes the human-panel/token-vote/dispute-delay path for supported deterministic markets.

Sources:
- https://chainlinktoday.com/chainlink-powered-world-prediction-markets-officially-launch-on-solana/
- https://crypto.news/world-prediction-market-third-resolution-model/
- https://genfinity.io/2026/09/10/world-xyz-solana-prediction-market-1-million-waitlist-chainlink/

Project-reported scale claims (>1m waitlist, >150k markets created) are retained only as project claims and are not treated as independent evidence of liquidity or economic importance.

## Why unexpected / potentially important
The mechanism differs materially from operator-adjudicated and optimistic-oracle/dispute-window settlement. A deterministic feed-driven venue can move the economically important race from `interpret public evidence -> anticipate adjudicator` toward `identify exact oracle input + update/finality semantics -> compare feed arrival with executable market repricing`. That changes both settlement-risk structure and the likely source of any timing asymmetry.

This is NOT a claim that a feed can be front-run or that an edge exists. The economically relevant question is whether public source data, Chainlink stream updates, venue state transitions and executable order books ever become measurably asynchronous under normal authorized/public access.

## Relation to known research
- Extends the existing pre-settlement / first-decidability lane, but changes the finality actor from human/rule interpretation to a programmed oracle workflow.
- Related to source-timing and deterministic state-lock research, but should not inherit positive assumptions from either.
- Distinct from Polymarket UMA dispute research: the absence/reduction of a dispute period removes one latency source while introducing feed/source/finality dependencies.
- Potentially relevant to cashflow-identity work if identical real-world outcomes trade simultaneously on human-resolved and feed-resolved venues with different close/resolution semantics.

## Transfer hypothesis
`same external event -> heterogeneous resolution architecture -> different close/finality/timing/risk premium -> potentially measurable cross-venue price or liquidity behavior`.

A second, narrower hypothesis is `deterministic oracle state transition -> temporary repricing lag`, but this remains entirely unproven and must be tested only from public/authorized data.

## Required data
- exact World market/rule definitions and oracle-source mappings;
- Chainlink Data Streams/CRE update and finality semantics for supported event types;
- public on-chain World market state transitions and redemption timestamps;
- point-in-time executable books/quotes if publicly obtainable;
- matched contracts on other venues with semantically identical payouts;
- network/transaction costs and settlement asset/collateral effects.

## Falsification
1. Semantic: reject cross-venue comparison where payout rules/source/finality are not identical enough.
2. Timing: measure source result, oracle update, market close, on-chain resolution and executable repricing prospectively. Reject timing-lag hypothesis if executable prices converge before/at oracle finality or observed lag is below costs/latency.
3. Economics: include depth, fees, network cost, failed/partial fills and collateral/finality. Reject if any apparent gap disappears after executable constraints.
4. Reliability counter-test: inspect outages/corrections/source exceptions; if deterministic resolution creates material basis risk, model that as risk rather than edge.

## Execution blockers
No verified World API/L2 capture path yet; exact oracle mappings/rules need primary documentation; liquidity unknown; project scale figures are self-reported; CASH/network frictions may dominate small gaps; automated settlement may make markets more efficient rather than less.

## Weak-signal score (0-5)
- novelty: 4
- source_strength: 4
- mechanism_distance_from_known: 4
- plausible_economic_impact: 4
- transferability: 4
- time_sensitivity: 3
- testability: 3
- data_availability: 3
- legality: 5

## Urgency
RESEARCH NEXT / NO TRADER. Add World as a venue to the oracle-architecture comparison and determine whether public on-chain state plus rule/oracle mappings are sufficient for a prospective timing study. Do not assume latency edge.
