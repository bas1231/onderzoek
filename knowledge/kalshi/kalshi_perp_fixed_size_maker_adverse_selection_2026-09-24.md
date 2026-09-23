# Kalshi perpetuals — fixed-size market maker adverse-selection evidence

Date: 2026-09-24 CEST
Status: `OBSERVED_SECONDARY / WATCH / NO_PROVEN_EDGE`
Role routing: PRIMARY_SCOUT + RECON_SCOUT -> MECHANICS (microstructure) -> RED_TEAM quick kill

## Observation
CoinDesk reported on 2026-09-21, updated 2026-09-22, that repeated fixed-dollar trade sizes dominated a sample of Kalshi BTC/ETH perpetual-futures volume. In the sampled ETH data, trades near $5,499 represented 57% of analyzed value; recurring sizes also appeared in BTC.

Source: https://www.coindesk.com/markets/2026/09/21/bitcoin-ether-perpetual-volumes-on-kalshi-are-dominated-by-an-unusual-repetitive-trade-data-shows

The same article reports Kalshi's explanation that the recurring flow came from one market maker posting fixed-size orders under a program paying a flat monthly amount for maintaining bids/offers within size/price limits. Kalshi reportedly stated that hundreds of distinct takers traded against those quotes and that the takers were consistently faster and profitable while the maker repeatedly traded at a disadvantage as prices moved elsewhere. The public feed does not identify accounts, so the account-level profitability statement is not independently verifiable from the public tape.

## Research significance
This is useful counterevidence for generic `maker == edge` and for naive reward/incentive farming. A compensated maker can still be adversely selected hard enough that faster takers capture the information/momentum component. It therefore strengthens the requirement that any FLB/maker candidate measure post-fill markouts, queue/fill selection, inventory, fees/rewards and regime/category dependence rather than infer edge from spread capture or maker incentives.

It is also a profitable-trader discovery lead in the opposite direction: the reported profitable side was not the designated/fixed-size maker but faster takers reacting as prices moved elsewhere. That suggests a falsifiable mechanism family: `external/reference-price move -> stale resting quote -> adverse-selection fill`. For this user's Starlink/non-colocated infrastructure this is *not* presumed executable; if the profitable takers require low-latency reaction, classify `EXECUTION_BLOCKED` for our setup.

## Three checks
1. Semantics/source: reputable secondary report; Kalshi's account-level explanation is reported but not independently reproducible from anonymous public feed. `PARTIAL`.
2. Data/reproducibility: repeating sizes can in principle be checked from public trades, but trader identity and per-account P&L cannot. No point-in-time L2 reproduction performed here. `INCOMPLETE`.
3. Economics/execution: no synchronized reference-price/L2/fee/latency corpus, so no net edge claim. `FAIL/UNKNOWN`.

## Red-team quick kill
Do not turn this into `follow the fast takers` or `snipe stale quotes`. The observed report does not establish a reproducible retail-speed edge, and the mechanism may be latency-sensitive. The only justified next test is a passive, historical/point-in-time measurement of adverse-selection markouts and stale-quote lifetime versus realistic Starlink latency, with no orders.

## Relation to existing work
- Reinforces `negative_evidence/LEDGER.md`: `maker zijn == edge` is false without adverse-selection/fill/inventory evidence.
- Relevant to `TASK-FLB-001`: include post-fill markouts and rewards; do not trade from generic FLB.
- Relevant to profitable-trader seed analysis as a public mechanism lead, but not verified trader-level P&L.

Economic conclusion: `NO_PROVEN_EDGE`.
