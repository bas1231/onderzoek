# Public weather bots — signal skill versus market edge

Date: 2026-09-19  
Status: **NEGATIVE_EVIDENCE / NO_PROVEN_EDGE**

## Why this record exists

Public implementations are not proof of our hypotheses, but they are useful adversarial evidence. This note records two materially different observations so later agents do not equate either forecast skill or stale public bot semantics with a trading edge.

## Observation A — public hourly bot still models legacy TWC semantics

A public repository, `jffrz78/kalshi-weather-bot`, describes itself as a Kalshi Hourly Temperature Bot. Its documented architecture quarantines ambiguous station/TWC source mappings and explicitly requires a validated TWC/Kalshi location identity. Its public documentation was last visibly updated before the September 2026 KWI/Synoptic source migration discovered in our separate KXTEMP research.

Interpretation:
- legacy TWC semantics do exist in public hourly-bot implementations;
- this makes source-regime drift a credible failure mode for external bots;
- it does **not** establish that executable Kalshi prices follow the wrong source;
- public code being stale is not market-edge evidence.

Source:
- https://github.com/jffrz78/kalshi-weather-bot

## Observation B — forecast skill did not become market edge

A separate public project, `mifisher/kalshi-weather-bot`, reports a retrospective study over roughly 14 months and four stations. The repository states that its weather model beat a climatology Brier baseline in all eight station/lead-time cells it evaluated, yet its three probability models produced negative returns after fees against historical Kalshi quotes over roughly 950 simulated trades.

The repository reports approximately:
- Brier scores around 0.065–0.15 versus climatology around 0.25;
- some cells passing its calibration gate and others failing due to seasonal bias;
- model-implied expected value around +15 to +18 cents/trade but realised replay returns around -3 to -4 cents/trade after fees.

Treat these numbers as **author-reported public-project evidence**, not independently reproduced facts. The methodological implication is still important: measurable forecast skill can coexist with no market edge, and historical market-quote replay can reverse an apparently attractive model-EV story.

Source:
- https://github.com/mifisher/kalshi-weather-bot

## Consequences for KAL-WX-E001

1. Do not promote KWI boundary-nowcasting merely because it beats persistence or another weather baseline.
2. Market-edge testing against contemporaneous executable side-specific prices remains mandatory.
3. Exact point-in-time fee provenance remains mandatory; small probability improvements can be economically irrelevant.
4. Source-migration research should test price alignment directly on episodes of material KWI-vs-legacy-source divergence. Do not infer mispricing from stale external bot code.
5. Public bot designs may be used as adversarial test generators, never as profitability proof.

## Three-angle classification

- Semantic/source angle: supports source-version drift as a real implementation risk.
- Signal/data angle: supports the possibility of genuine forecasting skill.
- Market/execution angle: provides negative evidence that signal skill alone survives Kalshi pricing and fees.

Economic status remains **NO_PROVEN_EDGE**.
