# Kalshi Weather Index free replay case — Miami 2026-09-09 12:00 EDT

Status: **OBSERVED / REPLAY_INCOMPLETE / NO_PROVEN_EDGE**

## Purpose
Freeze one publicly inspectable case before model tuning. This case may be used as a sanity/replay fixture but must not be treated as independent validation after being inspected.

## Contract/event
Series: `KXTEMPMIAH`
Event: `KXTEMPMIAH-26SEP0912`
Settlement time: 2026-09-09 12:00 EDT / 16:00 UTC
Settlement source semantics: Synoptic Data / Kalshi Weather Index Methodology.

Public final-outcome mirror confirms that `84° or above` (threshold >83.99°F) resolved **No** for this event. Therefore the canonical settlement value was below 84.00°F. Exact numeric settlement value is not asserted here because the public outcome page exposes threshold outcomes, not the exact canonical number.

## Execution observations
Public CryptoStruct free sample identifies `KXTEMPMIAH-26SEP0912-T82.99` as the busiest contract for the day, with approximately $4.9k turnover and 123 trades.

The public minute-level summary shows a large late repricing episode: trade prices were roughly in the 0.76–0.79 range around 15:38–15:39 UTC and reached roughly 0.97 by about 15:42 UTC. Trading continued into 15:59 UTC, with nonzero quoted spread and depth.

These are historical observations, not executable fill claims for a strategy. Minute aggregates do not establish queue position or an order-arrival fill.

## Why this case matters
The episode is compatible with several mutually exclusive explanations:
1. new weather/index information became available and was incorporated by the market;
2. ordinary order flow/liquidity caused the move;
3. a threshold-crossing probability changed from already-published canonical trend;
4. raw-station information arrived before canonical publication;
5. market makers repriced for reasons unrelated to a reproducible weather signal.

No explanation is promoted without point-in-time index/station evidence.

## Required three-angle replay
### 1. Semantic/source
- exact threshold comparator and settlement minute;
- exact point-in-time calibration/config version;
- final canonical settlement value if obtainable from authoritative/public index archive;
- contributor/QC/fallback state around the settlement minute.

### 2. Signal/reconstruction
Using only information available at each historical decision time (e.g. 15:30, 15:35, 15:38, 15:40 UTC), reconstruct:
- last published canonical index;
- canonical 1/2/5/10/15-minute trend;
- distance to 82.99/83.99 thresholds;
- station dispersion/raw-state only where receipt-time evidence exists.

Predefine prediction rule before evaluating additional cases. This inspected case may be development/sanity only, never untouched holdout.

### 3. Execution
Use raw L2/trades, not minute midpoint or close, to test:
- contemporaneous executable ask/bid and depth;
- spread/depth immediately before the price jump;
- realistic order-arrival delay;
- fees and partial fill;
- whether any positive signal existed before the price had already moved.

## Current conclusion
This case proves only that substantial late repricing occurred in an active Miami Weather Index threshold contract and that trading remained open close to the settlement minute. It does **not** prove that the move was forecastable or executable from a weather signal.

Economic status remains **NO_PROVEN_EDGE**.

## Public provenance
- Coinbase prediction page for `KXTEMPMIAH-26SEP0912`: threshold outcomes and Synoptic/Kalshi Weather Index rules.
- CryptoStruct KXTEMPMIAH public archive/free sample: contract-level and minute-level trades/order-book summaries.
