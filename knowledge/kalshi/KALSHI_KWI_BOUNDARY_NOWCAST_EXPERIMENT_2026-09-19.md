# Kalshi Weather Index boundary-nowcast experiment — preregistration 2026-09-19

Status: **HYPOTHESIS_UNTESTED / NO_PROVEN_EDGE**

## Experiment ID
`KAL-KWI-BND-001`

## Claim
For hourly Kalshi Weather Index contracts, the next settlement-minute KWI value may be forecast more accurately 5–30 minutes ahead from the already-published canonical KWI path than by a persistence baseline. If such signal improvement exists, a later and separate experiment may test whether executable Kalshi threshold prices underreact to it.

This experiment tests **signal edge only**. It must not be interpreted as market edge, execution proof, or profitability.

## Why this lane
The exact settlement-minute HF-ASOS observation generally arrives too late to create a clean pre-close information advantage. This experiment therefore deliberately avoids reliance on privileged/fast raw-feed access and uses only canonical KWI points that would already have been public by the decision timestamp.

## Point-in-time availability rule
A KWI point for observation minute `t` may only be used at decision times at or after its documented canonical publication time. For the current KWI methodology, the conservative default is `t + 300 seconds` unless contemporaneous evidence proves a different publication timestamp.

Backfilled / receipt-basis / non-settlement-eligible points must never be treated as contemporaneously available observations. Missing, degraded or configuration-ambiguous points are flagged; they are not silently filled from future data.

## Fixed forecast horizons
Evaluate exactly these horizons before the settlement minute `S`:
- `H30`: S - 30 minutes
- `H15`: S - 15 minutes
- `H10`: S - 10 minutes
- `H05`: S - 5 minutes

No additional horizon may be promoted from the same dataset after results are seen. Any new horizon is a new experiment.

## Forecast target
Primary continuous target:
- final canonical KWI point used for the hourly settlement at minute `S`.

Secondary threshold targets, only after a continuous signal is established:
- `1{KWI_S >= k}` for every contemporaneously listed directional threshold `k`.

Multiple thresholds for one city × settlement hour are one economic event, not independent samples.

## Models fixed before results
### B0 — Persistence
Predict `KWI_S` as the most recent canonical KWI point point-in-time available at the decision timestamp.

### B1 — 5-minute linear trend
OLS slope over the most recent 5 point-in-time-available canonical minutes; extrapolate to S.

### B2 — 10-minute linear trend
Same, 10-minute window.

### B3 — 20-minute linear trend
Same, 20-minute window.

No nonlinear model, weather-model input, station-level feed or hand-engineered regime filter is part of KAL-KWI-BND-001. If simple trend models fail, do not rescue this experiment by adding features post hoc.

## Data quality gates
For an event/horizon to be valid:
- exact city and settlement minute known;
- exact KWI configVersion/rules regime known where available;
- no future canonical point used;
- target settlement point valid and settlement-eligible;
- predictor points must have been public by the decision timestamp;
- no silent interpolation across unavailable/incomplete canonical minutes;
- source-transition/rules-version ambiguity = exclude with explicit reason, not impute.

## Three-angle method
### Angle 1 — semantic / availability proof
Verify contract settlement minute, KWI source/rules/config and conservative publication timing. Reconstruct exactly which canonical points existed at each decision timestamp.

### Angle 2 — signal / reproducibility
Run the four frozen models on chronological data. Primary metric: MAE. Secondary: RMSE. Report by horizon, city and pooled with city × local-date clustering where uncertainty is estimated.

For probabilistic threshold evaluation later, residual distributions must be fit only on development data; evaluate Brier score and log loss on later splits. A deterministic point forecast must not be converted to an ad-hoc probability after seeing outcomes.

### Angle 3 — adversarial / economic relevance
Before any market-edge promotion, test whether any signal gain is large specifically relative to contract boundary spacing and whether it survives on later untouched data. Only a separate experiment may then join the frozen forecasts to contemporaneous executable bid/ask/L2, fees, depth, partial-fill and latency evidence.

## Temporal split discipline
Historical KWI data may be used for development only if its canonical values are final/reproducible and point-in-time availability is reconstructed conservatively.

Initial split plan for data available before this preregistration:
- development: earliest available KWI history through 2026-09-09 inclusive;
- validation: 2026-09-10 through 2026-09-14 inclusive;
- untouched historical holdout: 2026-09-15 through 2026-09-18 inclusive.

The 2026-09-09 Miami 12:00 case has already been inspected qualitatively and is therefore **not** untouched evidence; it remains development/example material only.

If source/config transitions make these ranges non-comparable, report the regime split and downgrade the historical test rather than redefining dates after seeing performance.

## Success / failure interpretation
Primary comparison is each trend model versus B0 persistence at the same horizon.

A `RESEARCH_POSITIVE` signal result requires:
- improvement versus persistence in validation;
- same direction of improvement in untouched holdout;
- no dependence on one city/day/config anomaly;
- no point-in-time leakage or receipt-basis contamination.

Magnitude and uncertainty must be reported; no fixed profitability claim follows from a statistically positive signal. If improvement is tiny relative to hourly threshold spacing or unstable across splits, classify as economically weak even if MAE is numerically lower.

`TESTED_NEGATIVE` if all frozen trend models fail to improve persistence out-of-sample or any apparent improvement disappears under the point-in-time/data-quality gates.

## Explicitly forbidden post-hoc rescue
Do not, within this experiment:
- choose the best city after seeing results and call it the strategy;
- add a new horizon because it performed better historically;
- add NWS/GFS/ECMWF/TWC/station inputs after the simple models fail;
- drop losing weather regimes after inspecting P&L;
- tune a boundary-distance filter on validation/holdout;
- infer market edge from forecast accuracy alone.

Any such change requires a new experiment ID and new untouched data.

## Execution blocker
No Kalshi trade is justified by KAL-KWI-BND-001 alone. Even a strong signal must separately pass:
`signal edge -> market edge on contemporaneous executable L2 -> fees/depth/slippage/latency -> prospective shadow -> authorized micro-live`.

## Current status
Preregistered before broad historical model comparison. Economic status remains **NO_PROVEN_EDGE**.
