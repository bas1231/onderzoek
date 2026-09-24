# Turbine 4,904-strategy KXBTC15M failure-memory lead — 2026-09-24

Status: `DISCOVERY_EVIDENCE / CLAIM_ONLY / NO_PROVEN_EDGE`

## Source
Public Turbine Studio article dated 2026-09-21: `https://www.turbinefi.com/blog/do-automated-trading-bots-make-money-prediction-markets-2026`.

## Observation
The publisher reports a systematic backtest of 4,904 automated strategies on Kalshi's 15-minute BTC market. It reports 102 profitable strategies (2.1%), median strategy return -14.53%, and a large reversal versus a prior run that had reported 69.5% profitable. The publisher attributes most of that reversal to a more realistic cost model while noting the evaluation window also moved. It further reports that the ten worst strategies still won about 62-63% of trades while losing roughly 75-78%, and that an archetype that looked best in one run was profitable in only 7 of 4,290 variants nine days later. Reported maker/taker stratification says takers averaged -31.46% per contract, makers -9.64%, with only makers buying at 50c+ positive in that analysis (+2.6%).

These are publisher claims, not independently reproduced Research-OS results. Exact strategy generation, sampling dependence, fill assumptions, fee/rebate treatment, timestamps, survivorship and executable point-in-time orderbook provenance still require audit.

## Research significance
This is stronger Failure Memory than the earlier anecdotal ~40-experiment community post because it reports thousands of variants and explicitly demonstrates cost-model and window sensitivity. It supports these guardrails:

- high win rate is not evidence of positive EV;
- broad automated search creates severe multiple-testing/adaptive-selection risk;
- a profitable archetype in one window can collapse under nearby parameter/window changes;
- maker-versus-taker classification is insufficient without fill, markout, fee/reward and adverse-selection evidence;
- generic `favorite + maker` remains an experiment hypothesis, not a trading rule.

## Dynamic specialist — MARKET_RESEARCH / behavioral + microstructure interface
Decisive question: does the reported `maker + price >= 50c` survivor justify promotion of KAL-FLB-002?

Result: `NO`. The result is interesting enough to refine the preregistered FLB/maker experiment, but not enough for promotion. The decisive test must freeze category/price buckets and maker/taker definition in advance, use contemporaneous executable books/fills, include fees/rewards and post-fill markouts, and test on untouched later data. Parameter-family multiplicity must be recorded.

## Red-team QUICK_KILL
The inference `2.6% reported maker return -> reproducible edge` fails now because provenance and independent reproduction are absent; the publisher itself reports extreme regime/cost-model instability. This is a cheap kill of the promotion inference, not of the underlying candidate.

## Routing
- Link to `KAL-FLB-002` / `TASK-FLB-001` as experiment-design evidence.
- Add to profitable-trader/failure-memory lane as a stronger public negative-evidence lead.
- No Independent Reproducer yet; first obtain exact reproducible methodology/data or build an independent preregistered test.

Economic conclusion: `NO_PROVEN_EDGE`.
