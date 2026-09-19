# Kalshi Weather source-migration mispricing hypothesis — 2026-09-19

Status: **HYPOTHESIS_UNTESTED / NO_PROVEN_EDGE**

## Claim
A transition or coexistence between older hourly-temperature settlement semantics (The Weather Company references in general Kalshi weather documentation) and newer contract-specific Kalshi Weather Index / Synoptic Data semantics may create temporary mispricing when traders, bots or data pipelines use the wrong settlement model.

This is a semantic-adoption hypothesis, not a proven market edge.

## Angle 1 — semantic / source proof
Evidence of documentation divergence exists:
- Kalshi's general Weather Markets help article dated 2026-07-22 says hourly temperature markets settle using The Weather Company and weather.com/kalshi.
- Newer CFTC-certified Kalshi Weather Index products explicitly define regional/city indices based on ASOS inputs and Synoptic Data.
- A concrete KXTEMPMIAH contract for 2026-08-24 states Synoptic Data / Kalshi Weather Index Methodology as the authoritative source.

Agent rule: contract-specific rules and contemporaneous rules/version always override generic help-center descriptions. No market may be assigned TWC or Synoptic semantics from ticker/title alone.

## Angle 2 — independent/adversarial evidence
The semantic difference is discoverable by other builders. Public project/research status has already referenced KXTEMPMIAH Synoptic/MIAWINDEX work. Therefore 'nobody else noticed the source change' is not an acceptable mechanism assumption.

Historical market-activity summaries also show a rapid increase in KXTEMPMIAH L2 update activity and narrower spreads during the second half of August 2026. This is only observational and must not be causally attributed to the source transition, but it is consistent with increasing automated participation/competition rather than a persistent untouched semantic error.

## Angle 3 — required market/execution test
To test genuine source-migration mispricing, archive for each contract/event:
1. exact point-in-time contract rules/source/version;
2. a TWC-implied probability distribution using only contemporaneously available TWC information;
3. a Kalshi-Weather-Index-implied probability distribution using only contemporaneously available canonical/raw information;
4. simultaneous executable Kalshi bid/ask/full L2 and fee metadata.

The test is specifically conditional on **material source divergence**. Measure whether executable Kalshi prices track the correct source distribution or the obsolete/wrong-source distribution.

Suggested primary statistic:
- on episodes where |P_index - P_TWC| >= a preregistered threshold, compare Brier/log-loss and executable expected value of each model against eventual contract settlement.

Do not select divergence thresholds after seeing P&L.

## Falsification
Reject or downgrade the hypothesis if:
- prices consistently track the correct source as quickly as the divergence becomes observable;
- wrong-source alignment disappears after controlling for stale UI/mirror prices;
- all apparent gains occur only around the transition week and do not repeat on untouched data;
- fees/spread/depth remove the conditional edge;
- the exact historical source/rules version cannot be reconstructed point-in-time.

## Important negative evidence
The presence of stale/general Kalshi documentation is not itself an edge. Public builders already monitor the Synoptic/MIAWINDEX semantics, and KXTEMPMIAH shows substantial automated order-book activity. A persistent semantic-arbitrage assumption is therefore weak without direct price-alignment evidence.

## Current conclusion
The source/documentation mismatch is real enough to justify a narrowly defined conditional test, especially around periods of large TWC-vs-Kalshi-Index divergence. There is currently no evidence that executable market prices systematically follow the wrong source, so economic status remains **NO_PROVEN_EDGE**.
