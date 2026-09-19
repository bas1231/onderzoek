# Kalshi Weather Index — source transition / reconstructable hourly settlement

Date: 2026-09-19
Status: **RESEARCH_POSITIVE (semantic/source layer only) — NO_PROVEN_EDGE**

## Claim

Current/new Kalshi hourly temperature markets are not generically a The Weather Company black box. The newer `KXTEMP*` / Weather Index contracts can settle on the **Kalshi Weather Index**, a deterministic minute-resolution multi-station index calculated by Kalshi from public/observable ASOS inputs delivered through Synoptic Data.

This materially changes the research target: for these contracts, model the contract-specific Kalshi Weather Index and its publication/finality rules rather than assuming `hourly = TWC`.

## Primary evidence

### Miami

CFTC product filing 62610, KalshiEX, certified 2026-08-12:
- Rulebook: `MIAWINDEX`.
- Methodology Version 1.0, initial configuration `miami-temperature-v1.0`.
- Five member ASOS stations, equal base weight 0.20:
  - KMIA — Miami International Airport
  - KOPF — Miami-Opa Locka Executive Airport
  - KFLL — Fort Lauderdale-Hollywood International Airport
  - KFXE — Fort Lauderdale Executive Airport
  - KPMP — Pompano Beach Airpark
- Primary inputs are one-minute HF-ASOS readings (`*1M`) delivered through Synoptic Data PBC, network 258.
- Sole fallback is the same station's genuine official ASOS METAR/SPECI, max age 75 minutes, only after primary failure.
- Eligibility deadline is event minute `t + 300s`; later-arriving observations are excluded from canonical calculation.
- Quorum: at least 4 members and available base-weight share >=0.80.
- Calculation is in °C at full source precision and final Index output is rounded to nearest 0.01°F.
- Initial offsets in filing: KMIA 0.0°C, KOPF -0.5°C, KFLL 0.0°C, KFXE 0.0°C, KPMP 0.0°C; city reference -0.10°C. Offsets can be refreshed under the methodology, so live version/config provenance is mandatory.

Primary source:
- CFTC filing page: https://www.cftc.gov/IndustryOversight/IndustryFilings/TradingOrganizationProducts/62610
- Public filing PDF: https://www.cftc.gov/filings/ptc/ptc08122615995.pdf

### New York City

CFTC product filing 63739, KalshiEX, certified 2026-09-09:
- Rulebook: `NYCWINDEX`.
- Methodology Version 1.0, initial configuration `nyc-temperature-v1.0`.
- Eight equal-weight ASOS members: KLGA, KEWR, KTEB, KCDW, KHPN, KFRG, KSMQ, KISP.
- Same 5-minute eligibility deadline / canonical publication architecture; NYC-specific fallback and QC parameters apply.

Primary source:
- CFTC filing page: https://www.cftc.gov/IndustryOversight/IndustryFilings/TradingOrganizationProducts/63739
- Public filing PDF: https://www.cftc.gov/filings/ptc/ptc09092624308.pdf

## Settlement semantics that matter

For an `at` contract, the Index Settlement Value is the latest canonical observation whose event time is at or before the settlement time and no more than 60 minutes earlier. Determination occurs no earlier than 5 minutes after settlement time.

A canonical Index observation, once initially published, is final for contract purposes; later restatements/corrections/removals are not used, subject to the Market Outcome Review Process under Rule 7.1.

If there is no qualifying canonical observation in the permitted window, or an Expiration Value otherwise cannot be determined, Rule 7.1 applies. Therefore a raw station value or forecast is never by itself a settlement proof.

## Current-market observation / candidate

On 2026-09-19 the official Kalshi page for Miami 11:00 EDT (`KXTEMPMIAH-26SEP1911`) displayed a candidate threshold `83° or above` with a visible Yes buy around 76¢ while the page's displayed chance was around 85% during discovery.

Official market page:
https://kalshi.com/markets/kxtempmiah/hourly-directional-miami-temperature/kxtempmiah-26sep1911

This is **candidate discovery only**. Per the research protocol:
- UI chance is not an executable probability proof;
- a web-displayed buy price is not contemporaneous full-L2 execution evidence;
- current index/config version, fees, depth, latency and partial-fill risk are not yet captured here;
- no independent calibrated probability > market price has yet been proven.

Status of this Miami candidate: **UNPROVEN / DO NOT PROMOTE TO BUY**.

## Important source/version-drift correction

Earlier generic Kalshi help material described hourly temperature as settling via The Weather Company. The newer CFTC-certified Weather Index contracts show a different contract family/source architecture. Therefore agents must not use a global rule such as `hourly = TWC` or infer settlement source from category labels.

Required rule from now on:

> Resolve settlement semantics by exact series/event/rulebook + current methodology/configuration version. Generic help pages and older contract families are background only.

This does **not** imply that all daily or all hourly weather contracts share one source. Source/rules version must be captured per series/event.

## New research hypothesis

`KAL-WXINDEX-001` — **Kalshi Weather Index nowcast / market-lag hypothesis**

Hypothesis: 1–4 hours (and separately 5–60 minutes) before a Weather Index settlement minute, the contract-specific Index value can be probabilistically forecast from its exact member-station state/trend, solar/time-of-day, dew point, wind/advection, cloud, pressure, precipitation, neighboring observations, and numerical guidance more accurately than strong baselines; under a subset of conditions, executable market prices may underreact.

Signal edge and market edge remain separate gates.

### Required data

- immutable raw Kalshi Weather Index points with event time, publication/retrieval time, status, contributors, config version and receipt-basis/eligibility where exposed;
- contemporaneous configuration/calibration timeline;
- exact member HF-ASOS and fallback METAR/SPECI observations with observation and retrieval timestamps;
- point-in-time forecast/model guidance;
- simultaneous executable Kalshi bid/ask/full L2, fees, size and timestamps;
- final canonical Index value/outcome.

### Baselines

1. latest published Index persistence;
2. recent Index trend extrapolation;
3. weighted member-station nowcast under exact methodology;
4. public forecast baseline;
5. Weather Runner combination.

### Falsification / three-angle test

1. **Semantic/source:** reproduce historical canonical index points from the exact effective configuration and eligible station inputs, including QC/fallback/quorum edge cases.
2. **Signal/data:** pre-register horizons/features and test temporal development -> validation -> untouched holdout; compare CRPS/Brier/log loss/calibration against persistence/trend and strong forecast baselines.
3. **Market/execution:** prospectively join frozen probabilities to contemporaneous L2; require net positive edge after fees, depth, latency and partial fills, then shadow before any micro-live decision.

### Kill criteria

- public market/index data already incorporates the same station information fast enough that no prospective price lag survives realistic latency;
- index reconstruction cannot be made point-in-time because receipt-time/eligibility/QC inputs are unavailable;
- signal improvement exists but no improvement versus executable market price;
- fees/spread/depth destroy the conditional market edge;
- apparent edge is driven by one city/config/threshold or post-hoc filtering.

## Economic status

`NO_PROVEN_EDGE` remains unchanged.
