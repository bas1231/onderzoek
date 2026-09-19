# Kalshi Weather Index pre-publication / ultra-short nowcast hypothesis — 2026-09-19

Status: **HYPOTHESIS_UNTESTED / NO_PROVEN_EDGE**

## Refined claim
For Kalshi hourly Weather Index contracts, a trader may be able to use **low-latency HF-ASOS observations from the final few minutes before settlement (for example S-2/S-3)** to improve the prediction of settlement-minute index value S beyond the last already-published Kalshi canonical point.

This is an ultra-short nowcasting / information-lag hypothesis. It is **not** a deterministic source lock and **not** a proven market edge.

## Rejected sub-hypothesis — exact settlement-minute raw observation before close
The stronger initial idea was that the raw HF-ASOS observations for settlement minute S could be obtained and used to reconstruct the canonical S value before trading ended.

**Status: TESTED_NEGATIVE / ROUTE NARROWED.**

Primary contract rules state that for a single-minute `at` contract, Last Trading Time is the end of the specified time period / settlement minute. The underlying one-minute HF-ASOS observation normally arrives about 2–5 minutes after observation time, while Kalshi's canonical eligibility/publication process for minute S runs to S+300 seconds. Therefore the raw S observation is normally available only after the trading deadline and cannot safely be treated as pre-close information.

The remaining hypothesis is narrower: before the end of S, low-latency raw observations for S-2/S-3 may sometimes be available while the most recent published canonical index is older (roughly around S-5). Those fresher observations may improve the forecast of S.

## Semantics / primary-source evidence
Primary filing: CFTC product filing 62610 / MIAWINDEX (KalshiEX, 2026-08-12).

Key rules:
- Miami Index uses five ASOS members: KMIA, KOPF, KFLL, KFXE, KPMP, equal base weights 0.20.
- Primary source is each station's one-minute HF-ASOS record: KMIA1M, KOPF1M, KFLL1M, KFXE1M, KPMP1M via Synoptic HF-ASOS network 258.
- Fallback is genuine official ASOS METAR/SPECI for the same station, max age 75 minutes.
- Eligibility deadline is event minute t + 300 seconds; observations arriving later are excluded from canonical calculation.
- Canonical point is calculated/published at t+300s and is final for settlement once published, subject only to Rule 7.1 outcome review.
- Numeric index requires >=4 members and >=0.80 available base-weight share.
- Miami v1.0 offsets in the filing: KMIA 0.0C; KOPF -0.5C; KFLL 0.0C; KFXE 0.0C; KPMP 0.0C; city reference B=-0.10C. Configuration can be updated prospectively and must therefore be version-locked point-in-time.
- `At` contracts settle on the latest canonical point at or before the settlement minute, max 60 minutes old.
- Last Trading Time for a single-minute contract is the end of that specified minute.

### Algebraic simplification for Miami
When all five members are accepted, the calibration offsets cancel in the weighted-index formula and the Miami Index equals the arithmetic mean of the five raw station temperatures, subject to the official QC/eligibility process and final rounding.

For a 4/5-member accepted set, the calibration adjustment relative to the simple available-station mean is small but not zero and must still be applied from the point-in-time configuration. QC, fallback, contributor count and configuration version remain mandatory.

## Independent data-path evidence
Synoptic documents HF-ASOS as a low-latency provisional real-time stream. Under normal operation, the upstream one-minute observations usually arrive about 2–5 minutes after observation time. Synoptic processing after provider availability is generally fast, and its Push Streaming product is positioned as the minimum-latency path.

This materially weakens the direct-S route because S itself normally arrives after market close. It leaves only a possible freshness advantage from S-2/S-3 observations.

### Access / robustness blocker
The lowest-latency Synoptic Push route is a higher-tier commercial feature. Open-access API performance can vary. An independent NOAA/MADIS route exists for public one-minute ASOS data, but ordinary public OMO processing is organized in five-minute batches and continuous real-time distribution uses registered FTP/LDM/text/XML access.

Therefore a positive result must distinguish **model edge** from **premium-feed latency edge**. If profitability requires privileged/commercial feed speed that normal market makers also consume and the advantage disappears at realistic Starlink/order-arrival latency, this lane should be classified non-robust or non-executable for this project.

## Market/execution evidence
Public third-party historical summary for KXTEMPMIAH indicates substantial trading activity, many L2 updates and recent quoted spreads often in the high-single-digit cent range. This only establishes that the market is active enough to justify an execution test. It does not establish a stale-price window or profitable edge.

## Three-angle test plan
### Angle 1 — semantic / source proof
For every settlement event:
1. archive exact Kalshi contract/rules/settlement minute/Last Trading Time;
2. archive Kalshi weather-index response, calibration/config version and contributor/QC detail;
3. archive the exact station set and fallback/QC outcome used by the canonical point;
4. fail closed on config drift, unavailable quorum, Rule 7.1 ambiguity, source mismatch or unmatched settlement semantics.

### Angle 2 — signal / independent reconstruction
Prospectively collect raw HF-ASOS arrivals with **local receipt timestamps** for the five Miami stations.
At frozen decision timestamps before close, compare models that use only information truly available then:
- last published canonical point (baseline);
- persistence/trend on canonical index history;
- freshest raw-station state available at decision time, especially S-5 through S-2;
- station dispersion and 1/2/5/10-minute trend;
- fallback/QC-aware weighted reconstruction;
- optional simple calibrated residual distribution.

Primary question: does the freshest legally/publicly available raw state improve prediction of S out-of-sample versus the last published canonical index and simple trend baselines?

Metrics: MAE/CRPS for the continuous index and Brier/log-loss/calibration for contract thresholds, with temporal/event grouping and untouched holdout.

### Angle 3 — market / execution proof
At exactly the same frozen timestamps archive contemporaneous executable Kalshi bid/ask/full L2 for the complete threshold ladder.
Measure:
- whether price already reflects the fresher station information;
- executable size and depth walking;
- exact fees/version;
- partial fill and stale-book rejection;
- signal-to-order arrival latency under the actual network path;
- edge decay from raw-data receipt to hypothetical fill;
- settlement/capital lock-up.

No UI chance, midpoint or last-trade fills.

## Primary falsification questions
1. At the last realistically executable timestamps, are S-2/S-3 observations actually available often enough to be newer than the canonical-index baseline?
2. Do those fresher observations materially improve prediction of S out-of-sample?
3. Does the market price move on the same raw-feed information before a realistic order could arrive?
4. Is any apparent edge merely a premium-feed / latency race rather than a reproducible forecasting edge?
5. Is edge concentrated in rare outages, missing stations, degraded points or one configuration period?
6. Does any positive result survive fees, full depth and arrival latency?

## Kill criteria
Mark **TESTED_NEGATIVE**, **EDGE_NOT_EXECUTABLE** or **EDGE_TOO_SMALL** as appropriate if:
- at frozen decision time the freshest practicably accessible station observations are not materially newer than the latest published canonical point;
- the fresher raw state gives no stable out-of-sample improvement versus canonical-index persistence/trend;
- the market reprices the same information at least as fast as our realistic signal→order path;
- positive episodes vanish under L2, fees, partial fills or realistic arrival latency;
- the only useful information advantage requires a commercial minimum-latency feed and is competed away under our infrastructure;
- edge depends on post-close, late, backfilled, revised or retrospectively selected observations;
- results are dominated by one station/configuration/feed anomaly or sample remains insufficient.

## Current conclusion
The Weather Index product creates a reproducible minute-level settlement target and is structurally more transparent than a TWC black box. However, the strongest original pre-publication idea — using the raw settlement-minute observation itself before close — is rejected by timing. The only remaining information-lag hypothesis is a smaller S-2/S-3 freshness advantage, which currently carries a serious feed-access/latency blocker and still requires prospective signal and market tests.

Economic status remains: **NO_PROVEN_EDGE**.
