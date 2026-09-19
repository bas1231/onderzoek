# Research stop / handoff — 2026-09-19

Status: **RESEARCH PAUSED — NO_PROVEN_EDGE**

User instruction: stop active research after persisting the current state to Git.

## What was completed in this research run

### High-probability favorite scan
- College-football / high-probability Kalshi favorites were tested against no-vig sportsbook prices and independent models.
- Large apparent gaps mostly collapsed under vig correction, freshness checks, or model disagreement.
- A notable Louisiana-Monroe false positive was traced to stale/indexed Kalshi data.
- Conclusion: no proven >=80% underpriced favorite was found.
- Durable record: `negative_evidence/KALSHI_HIGH_PROBABILITY_FAVORITE_SCAN_2026-09-19.md`.

### MLB strikeout ladder scan
- Main strikeout lines were compared with external prop markets/models.
- Headline lines generally tracked broader market probabilities closely.
- Pitcher scratch/non-start semantics create an additional settlement branch and must be modeled explicitly.
- Conclusion: no simple headline-K mispricing proved.
- Durable record: `negative_evidence/KALSHI_MLB_STRIKEOUT_LADDER_SCAN_2026-09-19.md`.

### Kalshi Weather Index source transition
- Newer hourly weather contracts are not safely modeled as universally TWC-settled.
- Contract-specific rules/CFTC filings show Kalshi Weather Index / Synoptic settlement for newer series.
- Miami KWI uses multiple ASOS stations and a published deterministic methodology.
- Generic help-center wording must never override contemporaneous contract-specific source/rules.
- Durable record: `knowledge/kalshi/KALSHI_WEATHER_INDEX_SOURCE_TRANSITION_2026-09-19.md`.

### Pre-publication Weather Index hypothesis
- Original strong version ('see exact settlement-minute raw ASOS before close') was materially weakened.
- HF-ASOS settlement-minute observations normally arrive after the settlement minute; exact S-data is generally too late to trade before close.
- Remaining narrower hypothesis: fresher S-2 / S-3 station state may improve the forecast of settlement minute S versus the last already-published canonical index.
- Major blocker: fastest Synoptic push access is a commercial latency-sensitive feed; this risks becoming a feed/latency race rather than a defensible model edge.
- Durable record: `knowledge/kalshi/KALSHI_WEATHER_INDEX_PREPUBLICATION_HYPOTHESIS_2026-09-19.md`.

### Source-migration mispricing hypothesis
- Documentation divergence between old TWC semantics and new KWI/Synoptic semantics is real.
- However, same-hour dual-source overlap was **not proven**.
- Chicago on 2026-09-10 provides evidence of an intra-day regime transition: old TWC-style series at an earlier hour, new KWI/Synoptic series at a later hour.
- Therefore this must be treated as a source/rules regime break, not as proven cross-source arbitrage.
- Public evidence indicates other builders are already aware of Synoptic/MIAWINDEX semantics, weakening any 'nobody noticed' thesis.
- Durable record: `knowledge/kalshi/KALSHI_WEATHER_SOURCE_MIGRATION_MISPRICING_HYPOTHESIS_2026-09-19.md`.

### Frozen free replay case
- Miami, 2026-09-09, 12:00 EDT was frozen as a replay case before further tuning.
- Historical market data showed a large late repricing in the relevant threshold contract (roughly high-70s cents to high-90s cents shortly before settlement).
- This is an observed episode, not evidence of edge.
- The open question is whether canonical KWI state available before the repricing would have predicted it prospectively.
- Durable record: `knowledge/kalshi/KALSHI_WEATHER_INDEX_FREE_REPLAY_CASE_2026-09-09.md`.

### Boundary-nowcast experiment preregistration
- Before broad data inspection, the KWI boundary-nowcast test was preregistered.
- Fixed decision horizons: 30 / 15 / 10 / 5 minutes before settlement.
- Primary baseline: persistence / last published canonical KWI.
- Simple challengers: fixed short linear trends (5 / 10 / 20 minutes); no post-hoc horizon selection.
- First gate is signal quality on final KWI, not P&L.
- Market/execution tests only follow if signal edge exists out-of-sample.
- Durable record created in this run (commit `2368cda`).

## Important corrections made during falsification

1. **Do not say hourly weather = TWC.** Source/rules are series/version-specific.
2. **Do not say hourly weather = KWI either.** Historical series can differ; source migration occurred by series/city/time.
3. **Do not claim old/new source overlap without exact same-hour proof.** Current state is `UNPROVEN`.
4. **Do not treat UI 'chance', search snippets, mirrors, midpoint or last trade as executable price.**
5. **Do not promote weather signal edge to market edge without contemporaneous L2, fees, depth and latency.**
6. **Do not build a latency race by accident.** Commercial feed advantage is a blocker for the project's intended architecture.

## Current open hypotheses — NOT proven

### H-KWI-BOUNDARY
Can published canonical KWI history 30/15/10/5 minutes before settlement predict the next settlement-hour index materially better than persistence, especially near integer contract boundaries?

Required next evidence if research resumes:
- immutable canonical KWI history with configVersion/contributor metadata;
- temporal split and untouched holdout;
- MAE/CRPS and threshold Brier/log-loss;
- then simultaneous Kalshi executable L2, fee/depth/latency replay;
- prospective shadow before any micro-live action.

### H-KWI-SOURCE-DIVERGENCE
When contemporaneous TWC-implied and KWI-implied settlement distributions materially diverge, do executable Kalshi prices track the correct contract source fast enough?

Required next evidence if research resumes:
- exact point-in-time rules/source version per event;
- contemporaneous TWC and KWI distributions;
- preregistered divergence threshold;
- simultaneous executable L2;
- no stale UI/mirror proxies.

### H-KWI-FRESH-SENSOR
Can legitimately available pre-close S-2/S-3 HF-ASOS information improve S prediction beyond the last published KWI, without requiring a commercial latency race?

Current status: weak / fragile. Kill if public-access latency is not consistently early enough or if price incorporates the information at least as fast.

## Economic state

**NO_PROVEN_EDGE**

No live order was justified by this research run.
No claim of structural profitability is supported.

## Relevant commits from this run
- `2a882c0` — high-probability favorite scan negative evidence.
- `12d158b` — Weather Index source-transition research record.
- `9d661e8` — MLB strikeout-ladder negative evidence.
- `145ea0a` — initial pre-publication Weather Index hypothesis.
- `38aeece` — narrowed/corrected pre-publication hypothesis after latency/finality falsification.
- `b7f6cc8` — source-migration mispricing hypothesis.
- `b825b81` — frozen Miami free replay case.
- `01c4e2e` — correction: migration regime break; no proven same-hour overlap.
- `2368cda` — boundary-nowcast preregistration.

## Stop condition

Active research stops here per user instruction. No further browsing, testing, building, data acquisition, execution analysis or live trading should continue from this task unless explicitly restarted by the user.
