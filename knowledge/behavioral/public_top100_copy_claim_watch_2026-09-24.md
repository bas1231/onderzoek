# Public profitable-trader claim watch — top-100 flat-copy replay

Date: 2026-09-24
Status: CLAIM_ONLY / WATCH
Economic conclusion: NO_PROVEN_EDGE
Source class: public community claim (Reddit), independently unverified

## Observation
A public post dated 2026-09-23 claims a replay over the then top 100 traders on both Kalshi and Polymarket, using every observed buy during the prior 90 days, a flat hypothetical $100 stake per entry, and holding each copied entry to resolution. The author reports 84% of Kalshi top-100 and 86% of Polymarket top-100 profitable under that construction; median return on stake is claimed as 18.4% and 9.1% respectively. A sensitivity charging 4 cents per copied dollar is claimed to leave 74 Kalshi and 61 Polymarket traders profitable.

## Research-OS classification
This is discovery evidence only. It is not evidence that copy trading is prospectively profitable.

Decisive failure modes:
- leaderboard selection is ex-post winner selection and can create severe survivorship/selection bias;
- ranking at the end/start of the same evaluation window must be established point-in-time;
- only buys are scored while sells/exits are omitted, so the replay does not reproduce trader P&L or strategy;
- recorded trade price is not proof a follower could execute at that price, size or time;
- a flat 4-cent friction allowance is not a substitute for synchronized executable bid/ask, depth, latency, fees and market impact;
- correlated positions and repeated markets can make apparent sample size much larger than independent evidence;
- no untouched prospective cohort is supplied.

## Cheapest decisive test
Do not copy traders. Freeze a cohort using a point-in-time public leaderboard snapshot, freeze entry/following rules before outcomes, then prospectively shadow only future public entries with timestamped executable prices/depth. Compare against matched market/price-bucket baselines and report both gross and friction-adjusted results. Preserve exits separately rather than silently converting all buys to hold-to-resolution.

## Agent routing
PRIMARY_SCOUT/RECON_SCOUT: mechanism discovery and provenance.
SPECIALIST_MARKET_RESEARCH: selection bias, calibration and cohort design.
RED_TEAM: survivorship, lookahead, dependence and execution falsification.
Independent reproducer: only if a preregistered prospective cohort survives.

No live trading, orders, wallet/fund movement or paid data is authorized.
