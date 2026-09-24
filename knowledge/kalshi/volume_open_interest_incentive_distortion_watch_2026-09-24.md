# Kalshi incentive-volume / open-interest distortion WATCH — 2026-09-24

Status: WATCH / NO_PROVEN_EDGE

## Observation
Recent public reporting based on Kalshi's public API found highly concentrated repeated trade sizes in Kalshi BTC/ETH perpetual markets. CoinDesk reports that a $5,499 ETH-perp trade size represented about 57% of its sampled Sept. 17–20 volume, while recurring $2,500/$5,000 BTC-perp sizes represented about 54% of sampled volume. The same reporting notes a Sept. 16 rebate program that reduced fees to 0.003% for some self-clearing firms and paid market makers a rebate of the same size. Kalshi says the unusual patterns are typical of liquidity-incentive programs and says it does not believe a formal CFTC investigation is underway.

## Inference
Raw reported volume can be a poor proxy for independent executable demand or strategy capacity when incentive programs, repeated-size automation, rapid turnover, or low open interest dominate activity. A high-volume market must therefore not be ranked as economically attractive solely from gross volume.

## Research guardrail
For future candidate ranking and execution-capacity claims, preserve separately where available:
- gross traded volume;
- open interest / persistent exposure;
- unique or repeated trade-size concentration;
- incentive/rebate regime and effective time;
- spread/depth/lifetime and actual fill evidence;
- participant/access constraints.

Do not infer wash trading, self-trading, manipulation, or profitable maker economics without direct evidence. Incentive-adjusted turnover is a WATCH trigger, not an edge.

## Candidate consequence
No candidate promotion or kill. This is especially relevant to maker/informed-flow research and to any future volume-based market ranking. Recheck only when primary incentive terms, point-in-time public trade data, or candidate-specific executable evidence materially changes.

Economic conclusion: `NO_PROVEN_EDGE`.
