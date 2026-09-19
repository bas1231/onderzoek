# Kalshi Weather source-migration mispricing hypothesis — 2026-09-19

Status: **HYPOTHESIS_UNTESTED / NO_PROVEN_EDGE**

## Claim
A transition between older hourly-temperature settlement semantics (The Weather Company) and newer contract-specific Kalshi Weather Index / Synoptic Data semantics may create temporary mispricing when traders, bots or data pipelines use the wrong settlement model.

This is a semantic-adoption hypothesis, not a proven market edge.

## Angle 1 — semantic / source proof
Evidence of documentation divergence exists:
- Kalshi's general Weather Markets help material historically described hourly temperature markets using The Weather Company / weather.com/kalshi.
- Newer CFTC-certified Kalshi Weather Index products explicitly define regional/city indices based on ASOS inputs and Synoptic Data.
- Concrete newer KXTEMP contracts state Synoptic Data / Kalshi Weather Index Methodology as the authoritative source.

### Chicago cutover case
A sharper historical transition is documented for Chicago on **2026-09-10**:
- `KXTEMPCHIH-26SEP1010` (10:00 EDT) still names **The Weather Company**, coordinates/station reference **KORD/O'Hare**.
- `KXTEMPCHIHS-26SEP1011` (11:00 EDT) names **Synoptic Data / Kalshi Weather Index Methodology** for **Chicago Metro Area**.
- No old-series 11:00 contract or new-series 10:00 contract has been established.

Therefore the currently supported claim is a **sharp intra-day source/series cutover between 10:00 and 11:00 EDT**, not simultaneous same-hour coexistence.

**Correction / negative evidence:** exact same-city × same-settlement-minute overlap between old TWC and new KWI contracts is **UNPROVEN**. Do not model this transition as a cross-source arbitrage pair unless such overlap is independently proven later.

### Geographic measurement-function evidence
The migration is potentially more material than a documentation-label change because the old contract explicitly referenced KORD/O'Hare while the new product is a metro-area index.

A contemporaneous public METAR cross-check on 2026-09-10 shows that nearby Chicago stations can differ by contract-relevant amounts:
- around 14:51 UTC, KORD reported `T02220133` = **22.2°C ≈ 72.0°F**;
- around 14:53 UTC, KMDW reported `T02330161` = **23.3°C ≈ 73.9°F**;
- difference ≈ **1.98°F**.

Around the following hour:
- KORD 15:51 UTC: `23.3°C ≈ 73.9°F`;
- KMDW 15:53 UTC: `23.9°C ≈ 75.0°F`;
- difference ≈ **1.08°F**.

These are not settlement-value comparisons because observation minutes differ slightly and KWI is a calibrated multi-station index. They do establish that **metro spatial dispersion can easily cross one or more integer contract strikes**, so using a single-airport proxy can be materially wrong.

A secondary KWI tool labels Chicago with KMDW as its city reference/mapping, but this must **not** be interpreted as `KWI = KMDW`. Indeed, the 2026-09-10 11:00 EDT new-series outcomes imply the KWI settlement was between roughly **71.00°F and 71.99°F**, while KMDW's nearby 14:53 UTC METAR was about **73.9°F**. This is direct warning evidence that the exact multi-station calibration/weights are essential.

**Open semantic blocker:** exact Chicago KWI calibration members, weights, offsets, effective version and publication timestamp still require primary `/live_data/weather/chicago/calibrations` or equivalent CFTC methodology evidence. No geographic-divergence model may be promoted without this.

Agent rule: contract-specific rules and contemporaneous rules/version always override generic help-center descriptions. No market may be assigned TWC or Synoptic semantics from ticker/title alone.

## Angle 2 — independent/adversarial evidence
The semantic difference is discoverable by other builders. Public project/research status has already referenced KXTEMPMIAH Synoptic/MIAWINDEX work. Therefore 'nobody else noticed the source change' is not an acceptable mechanism assumption.

Historical market-activity summaries show substantial automated order-book activity in hourly weather markets. This is only observational and must not be causally attributed to the source transition, but it argues against assuming a persistent untouched semantic error.

The Chicago cutover itself does **not** show an impossible discontinuity: old 10:00 TWC threshold outcomes imply a final value between roughly 70.00°F and 70.99°F, while new 11:00 KWI outcomes imply roughly 71.00°F to 71.99°F. One hour of normal daytime warming can explain that difference, so it is not evidence of source-divergence mispricing.

The station-spread example above strengthens only the **mechanistic plausibility** that source/geometry matters around thresholds. It does not establish that Kalshi prices used the wrong source or that any executable edge existed.

## Angle 3 — required market/execution test
To test genuine source-migration mispricing, archive for each contract/event:
1. exact point-in-time contract rules/source/version;
2. a TWC-implied probability distribution using only contemporaneously available TWC information;
3. a KWI-implied probability distribution using only contemporaneously available canonical information and exact calibration version;
4. simultaneous executable Kalshi bid/ask/full L2 and fee metadata.

The test is specifically conditional on **material source divergence**. Measure whether executable Kalshi prices track the correct source distribution or the obsolete/wrong-source distribution.

Suggested primary statistic:
- on episodes where `|P_index - P_TWC|` exceeds a preregistered threshold, compare Brier/log-loss and executable expected value of each model against eventual contract settlement.

Do not select divergence thresholds after seeing P&L.

## Falsification
Reject or downgrade the hypothesis if:
- prices consistently track the correct source as quickly as the divergence becomes observable;
- wrong-source alignment disappears after controlling for stale UI/mirror prices;
- all apparent gains occur only around the transition week and do not repeat on untouched data;
- fees/spread/depth remove the conditional edge;
- the exact historical source/rules/calibration version cannot be reconstructed point-in-time.

## Important negative evidence
- The presence of stale/general documentation is not itself an edge.
- Public builders already monitor Synoptic/MIAWINDEX semantics.
- Exact same-hour old/new Chicago overlap is not established.
- A source cutover between adjacent hours cannot be used as direct TWC-vs-KWI A/B payoff comparison because meteorological state also changes between hours.
- `Chicago reference = KMDW` from a secondary tool does **not** mean `KWI = KMDW`; the observed Sep-10 outcomes contradict such a simplification.

## Current conclusion
The source/documentation mismatch, Chicago intra-day cutover and observed ~1–2°F spatial station dispersion make source/geometry divergence a **structurally plausible conditional research lane**. There is still no evidence that executable market prices systematically follow the wrong source, exact Chicago KWI calibration remains unresolved, and no same-hour cross-source arbitrage pair has been proven.

Economic status remains **NO_PROVEN_EDGE**.
