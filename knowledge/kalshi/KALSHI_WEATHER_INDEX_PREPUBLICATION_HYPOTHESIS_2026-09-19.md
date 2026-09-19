# Kalshi Weather Index pre-publication nowcast hypothesis — 2026-09-19

Status: **HYPOTHESIS_UNTESTED / NO_PROVEN_EDGE**

## Claim
For Kalshi hourly Weather Index contracts, a trader may be able to estimate the still-unpublished canonical settlement-minute index from the underlying HF-ASOS station network shortly before market close, creating a testable 1–5 minute information-lag hypothesis.

This is **not** a proven market edge.

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
- 'At' contracts settle on the latest canonical point at or before the settlement minute, max 60 minutes old.

## Independent data-path evidence
Synoptic documents the full HF-ASOS feed as a low-latency provisional real-time stream. Under normal operation it usually arrives 2–5 minutes after observation time. Synoptic platform processing after provider availability is generally under 10 seconds; push streaming can deliver within ~2 seconds after data become available.

This means there may sometimes be a small interval in which one or more underlying station observations are visible before the corresponding Kalshi canonical point is published at t+5m. However, the window may be zero when provider latency is near 5 minutes, and market close timing may eliminate the usable interval entirely.

## Market/execution evidence
Public third-party historical summary for KXTEMPMIAH reports, over 30 captured days through 2026-09-13:
- ~4,058 trades/day;
- ~$62.9k turnover/day;
- ~192 contracts traded/day;
- ~1.1m L2 updates/day;
- recent average quoted spreads roughly 6–10 cents on many days, though wider on earlier days.

This is only evidence that the series is active enough to justify an execution test. It is not evidence that a pre-publication signal survives executable prices.

## Three-angle test plan
### Angle 1 — semantic / source proof
For every event minute:
1. archive Kalshi weather-index response and calibration/config version;
2. archive detailed per-station contributors/QC dispositions;
3. archive exact contract strike/comparator/settlement minute/close time/rules version;
4. fail closed on config drift, unavailable quorum, Rule 7.1 ambiguity, or unmatched settlement semantics.

### Angle 2 — signal / independent reconstruction
Prospectively collect raw HF-ASOS arrivals with local receipt timestamps for the five Miami stations.
At each decision timestamp before close, reconstruct the best possible estimate of the future canonical settlement point using only observations already available then.
Compare against:
- persistence;
- last published canonical point;
- short trend 1/2/5/10 min;
- direct station-weight reconstruction with current calibration;
- fallback-aware reconstruction;
- optional simple probabilistic residual model.
Metrics: MAE, CRPS and threshold Brier/log-loss, time-split and grouped by settlement event.

### Angle 3 — market / execution proof
At exactly the same decision timestamps archive contemporaneous executable Kalshi bid/ask/L2 for the complete threshold ladder.
Calculate net expected edge after:
- fee schedule/version;
- depth walking;
- partial fill;
- arrival latency;
- stale-book rejection;
- capital lock-up.
No midpoint, UI chance or last-trade fills.

## Primary falsification questions
1. Do HF-ASOS readings actually arrive before last executable market time often enough to matter?
2. Does raw-station reconstruction predict the final canonical point better than the last already-published Kalshi index?
3. Does Kalshi price already incorporate the same raw-feed information before our decision timestamp?
4. Is the useful edge concentrated only in rare feed outages, degraded points or one station/config regime?
5. After fees/depth/latency, is any positive difference still executable?

## Kill criteria
Mark **TESTED_NEGATIVE** if any of the following is established prospectively:
- raw station observations relevant to the settlement minute almost never become available before last executable time;
- signal improvement versus last-published index is negligible/out-of-sample absent;
- price reacts at least as fast as our signal so no executable market edge remains;
- positive episodes vanish under full L2, fees or realistic order arrival;
- edge depends on post-close, backfilled, late, revised or retrospectively selected observations;
- sample remains too small or is dominated by one anomalous feed/config period.

## Current conclusion
The new Weather Index product removes much of the old TWC black-box uncertainty for this contract family and creates a reproducible minute-level settlement target. The pre-publication reconstruction mechanism is structurally plausible, but no signal edge, market edge or executable P&L has yet been demonstrated.

Economic status remains: **NO_PROVEN_EDGE**.
