# Nadex Macro Predictions microstructure trigger — 2026-09-22

Status: WATCH / NO_PROVEN_EDGE

## Observation
Primary CFTC filings received 2026-09-16 show three related CDNA/Nadex changes under 10-day review:

1. Macro Predictions Market Maker Program for crypto, FX, equity-index and commodity markets, with zero maker fees in exchange for specified two-sided quoting, spread, size and uptime obligations (CFTC filing 64136).
2. Macro Markets Volume Incentive Program with tiered weekly fee rebates and passive/aggressing volume measured separately (CFTC filing 64137).
3. Rule 13.1 amendments permitting fractional contract units and revising the default minimum quote increment to $0.001 per contract unless contract terms specify otherwise (CFTC filing 64138).

Primary provenance:
- https://www.cftc.gov/IndustryOversight/IndustryFilings/TradingOrganizationRules/64136
- https://www.cftc.gov/IndustryOversight/IndustryFilings/TradingOrganizationRules/64137
- https://www.cftc.gov/IndustryOversight/IndustryFilings/TradingOrganizationRules/64138

## Inference
Together these changes can materially alter prediction-market microstructure: finer ticks and fractional sizing can reduce minimum capital/granularity constraints; zero-maker-fee obligations can concentrate displayed liquidity; and separate passive/aggressive rebate accounting can alter maker/taker economics. This is a regime-change trigger only.

## What is NOT proven
- No executable market edge.
- No execution edge for this project.
- No proof that the user's accessible participant path qualifies for the market-maker or volume programs.
- No synchronized L2, fills, queue behavior, fee realization, or current contract-specific depth was captured.
- Filing status is 10 Day Review, so effective/current implementation must be verified before economics.

## Pre-Build Killer / falsification
Do not build from the filings alone. Cheap failure modes:
- incentive eligibility may require obligations or participant status incompatible with the project;
- zero maker fees can improve efficiency and erase, rather than create, mispricing;
- finer ticks can compress spreads without producing positive post-fill markouts;
- volume rebates can be dominated by adverse selection or unattainable thresholds;
- fractional sizing improves accessibility but not expected value.

## Next decisive question
Verify effective implementation and participant eligibility, then capture contemporaneous executable books/fees and test whether post-change spread, depth, queue/fill and post-fill markouts differ enough to create net economics after all constraints.

Economic conclusion: NO_PROVEN_EDGE.
