# KAL-WX-E001 — Weather Index signal + market edge

Status: **PREREGISTERED / NOT YET RUN**  
Economic status: **NO_PROVEN_EDGE**  
Date: 2026-09-19

## Question

Can the publicly observable Kalshi Weather Index and its detailed station/calibration state improve short-horizon prediction of the exact KXTEMP settlement outcome, and does any such signal remain absent from contemporaneous executable Kalshi prices?

This experiment is split into three independent proof angles. Passing one angle does not imply the others pass.

---

## Angle 1 — Rules / source / semantics

Before an event enters any model dataset, archive point-in-time:

- series ticker and metadata;
- event and market ticker;
- full rule text / rules_version if available;
- named settlement/source agency;
- threshold/comparator;
- observation clock/timezone;
- rounding/transformation rule;
- close timestamp;
- index config_version;
- calibration record that was already published at prediction time.

### Gate

An event is admissible only if the tested payoff can be computed unambiguously from the archived contemporaneous rule/source state.

### Failure

If source/rule semantics cannot be proven, label event `SEMANTICS_UNPROVEN` and exclude it from signal/economic scoring without backfilling rules later.

---

## Angle 2 — Signal edge

### Prediction horizons

Evaluate only predeclared horizons:

- T-240m
- T-180m
- T-120m
- T-60m
- T-30m
- T-15m
- T-5m

Prediction timestamp uses only information retrieved by or before that timestamp.

### Baselines

B0 — persistence: last known index value.  
B1 — 15-minute linear trend extrapolation.  
B2 — 30-minute linear trend extrapolation.  
B3 — weighted current station state using contemporaneous published configuration.  
B4 — nearest/primary station current observation when defined.  

No model is allowed to claim signal edge unless it improves against the strongest relevant baseline out-of-sample.

### Candidate feature families

- latest index value;
- 5/15/30m slopes;
- acceleration / slope change;
- contributor count;
- index status;
- receipt_basis;
- station dispersion;
- per-station residual to index;
- station observation age / received_at latency;
- config_version;
- days since latest published calibration;
- current calibration offset vector;
- calibration change indicator;
- local hour / solar-time proxy;
- distance to each contract threshold.

Features not present in the preregistration may be explored in development, but any material post-hoc discovery must receive a new experiment version before validation/holdout.

### Targets

Continuous target: final rule-authoritative hourly value where a continuous final value is recoverable.  
Binary targets: final YES/NO outcome for each KXTEMP threshold.

### Metrics

Continuous: MAE, CRPS where a distribution is emitted.  
Probability: Brier score, log loss, calibration, sharpness.  
AUC is secondary only.

### Splits

Temporal only, grouped at minimum by `city x local_date` so correlated thresholds from the same settlement cannot leak independently across splits.

1. development;
2. validation;
3. untouched final holdout.

Different threshold contracts from one hourly settlement are one economic event, not independent observations.

### Signal kill rule

Kill this version if the index-enhanced model fails to improve on the strongest preregistered baseline on the untouched holdout, or if improvement is driven by a tiny post-hoc city/horizon slice without independent confirmation.

---

## Angle 3 — Market / execution edge

Signal-positive events are joined to contemporaneous executable KXTEMP order books.

Required market fields:

- bid and ask at prediction timestamp;
- relevant L2 depth;
- book timestamp / receive timestamp;
- trades where useful;
- fee schedule and applicable overrides;
- close/lifecycle state.

### Market probability benchmark

Use executable side-specific prices, not UI percentages, midpoint or stale last trade. Where a model action would buy YES, benchmark against executable YES ask plus fees and conservative slippage; analogously for NO.

### Tests

1. Does the model improve Brier/log loss versus executable market-implied probability on the same timestamps?
2. Are there predeclared probability-gap buckets with positive conservative expected value after fees?
3. Does the opportunity survive available depth and partial-fill assumptions?
4. Does it remain in untouched holdout and later prospective shadow?

### Economic kill rule

Kill market-edge version if:

- market probabilities absorb the signal;
- gross edge disappears after fees/spread/depth;
- positive results require stale quotes or midpoint pricing;
- positive results depend on lookahead/backfilled index points;
- profitable cases disappear in untouched holdout.

---

## Adversarial fourth check

Where practical, independently reproduce the calculation using a second implementation or independently derived dataset. Explicitly search for:

- source-regime changes;
- calibration publication/effective-time leakage;
- backfilled index points treated as live;
- missing quorum minutes;
- revised station observations;
- timezone/DST mistakes;
- threshold `>` versus `>=` errors;
- correlated threshold double-counting;
- orderbook timestamp mismatch.

---

## Current source finding

Kalshi's current API documentation calls the Weather Index the canonical minute-resolution series behind hourly temperature markets and exposes detailed station observations plus an append-only calibration timeline. However, public source descriptions around KXTEMP settlement are currently conflicting: older/general Kalshi material mentions The Weather Company, while multiple recent KXTEMP contract distributions state Synoptic Data and Kalshi Weather Index Methodology. Therefore source semantics are a mandatory first gate, not an assumption.

## Promotion path

`SEMANTIC_PASS -> SIGNAL_VALIDATION_PASS -> SIGNAL_HOLDOUT_PASS -> MARKET_VALIDATION_PASS -> MARKET_HOLDOUT_PASS -> PROSPECTIVE_SHADOW_PASS -> separately authorized MICRO_LIVE`

No prior stage permits a claim of `PROVEN_EDGE`.
