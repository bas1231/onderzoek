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
A sharper historical transition is now documented for Chicago on **2026-09-10**:
- `KXTEMPCHIH-26SEP1010` (10:00 EDT) still names **The Weather Company**, coordinates/station reference KORD.
- `KXTEMPCHIHS-26SEP1011` (11:00 EDT) names **Synoptic Data / Kalshi Weather Index Methodology** for Chicago Metro Area.
- The old `KXTEMPCHIH` historical archive shows Sep 10 ending with the 10:00 EDT contract family; no old-series 11:00 contract has been established.
- Searches have not established a new `KXTEMPCHIHS` 10:00 contract.

Therefore the currently supported claim is a **sharp intra-day source/series cutover between 10:00 and 11:00 EDT**, not simultaneous same-hour coexistence.

**Correction / negative evidence:** exact same-city × same-settlement-minute overlap between old TWC and new KWI contracts is **UNPROVEN**. Do not model this transition as a cross-source arbitrage pair unless such overlap is independently proven later.

The old-series Sep 10 execution archive also shows only 130 files / 45 traded contracts versus 263 files / 153 traded contracts on Sep 9, consistent with the old series terminating part-way through Sep 10. This is supporting lifecycle evidence, not proof of why Kalshi changed the series.

Agent rule: contract-specific rules and contemporaneous rules/version always override generic help-center descriptions. No market may be assigned TWC or Synoptic semantics from ticker/title alone.

## Angle 2 — independent/adversarial evidence
The semantic difference is discoverable by other builders. Public project/research status has already referenced KXTEMPMIAH Synoptic/MIAWINDEX work. Therefore 'nobody else noticed the source change' is not an acceptable mechanism assumption.

Historical market-activity summaries show substantial automated order-book activity in hourly weather markets. This is only observational and must not be causally attributed to the source transition, but it argues against assuming a persistent untouched semantic error.

The Chicago cutover itself does **not** show a visible impossible discontinuity: old 10:00 TWC threshold outcomes imply a final value between roughly 70.00°F and 70.99°F, while new 11:00 KWI outcomes imply roughly 71.00°F to 71.99°F. One hour of normal daytime warming can explain that difference, so it is not evidence of source-divergence mispricing.

## Angle 3 — required market/execution test
To test genuine source-migration mispricing, archive for each contract/event:
1. exact point-in-time contract rules/source/version;
2. a TWC-implied probability distribution using only contemporaneously available TWC information;
3. a Kalshi-Weather-Index-implied probability distribution using only contemporaneously available canonical/raw information;
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
- the exact historical source/rules version cannot be reconstructed point-in-time.

## Important negative evidence
- The presence of stale/general documentation is not itself an edge.
- Public builders already monitor Synoptic/MIAWINDEX semantics.
- Exact same-hour old/new Chicago overlap is not established.
- A source cutover between adjacent hours cannot be used as direct TWC-vs-KWI A/B payoff comparison because meteorological state also changes between hours.

## Current conclusion
The source/documentation mismatch and Chicago intra-day cutover are real enough to justify a narrowly defined conditional test, especially on future episodes of large contemporaneous TWC-vs-KWI divergence. There is currently no evidence that executable market prices systematically follow the wrong source, and no same-hour cross-source arbitrage pair has been proven.

Economic status remains **NO_PROVEN_EDGE**.
