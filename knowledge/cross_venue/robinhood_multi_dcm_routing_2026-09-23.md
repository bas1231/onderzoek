# Robinhood multi-DCM event-contract routing — 2026-09-23

Status: `WATCH / NO_PROVEN_EDGE`

## Observation
Robinhood's official newsroom states that beginning 2026-09-08 it began routing a selection of football event contracts to Crypto.com | Derivatives North America / OG.com. The same announcement says Robinhood had already begun routing contracts in June to Rothera, a CFTC-licensed exchange and clearinghouse. Robinhood explicitly describes the purpose as routing event contracts to multiple venues.

Primary source: Robinhood newsroom, `Robinhood Teams Up With Crypto.com and OG.com to Expand Access to Prediction Markets Ahead of A Busy Fall`, published September 2026.

## Inference
A consumer-facing event-contract surface can no longer safely be treated as a single-venue execution source. Historical/prospective replay, fee provenance, market identity, settlement/rule provenance and executable-price capture should preserve the actual exchange/clearing route where exposed. Two visually similar contracts surfaced through one broker/frontend are not evidence of one order book or one fee/execution regime.

## Hypothesis
Multi-DCM routing could create temporary cross-route fragmentation or differential execution economics, but no synchronized executable evidence was captured here. It is therefore only a mechanics/microstructure discovery trigger.

## Red-team / failure modes
- Broker UI price or last trade is not proof of executable depth on a specific routed venue.
- Same event/title does not prove identical contract semantics across DCMs.
- Smart routing may remove rather than create a persistent discrepancy.
- Participant eligibility, fees, queue priority, settlement/finality and route selection may differ.
- No edge may be claimed without route-resolved contemporaneous bid/ask/L2, fees and payoff identity.

## Research Director
Preserve as execution-provenance rule. Escalate only if a candidate spans a broker/front-end with multiple possible DCM routes or if synchronized route-resolved prices become available. No strategy build or independent reproduction justified now.

Economic conclusion: `NO_PROVEN_EDGE`.
