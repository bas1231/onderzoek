# Hourly durable findings — 2026-09-20 15:00 CEST

Status: RESEARCH_ONLY / NO_PROVEN_EDGE

## PM-MICRO-DIRECTION-001 — Polymarket trade-direction inference is not proof-safe

Status: FACT_SUPPORTED_BY_ACADEMIC_PRIMARY / METHODOLOGY_GUARDRAIL
Roles: microstructure, informed_flow, chief_falsifier

A 2026 Polymarket microstructure paper using a continuous public WebSocket order-book archive joined to authoritative on-chain OrderFilled records reports that trade direction inferred from the public order-book feed agrees with on-chain ground truth only about 59% of the time (panel mean 0.615, 95% CI [0.58, 0.65]). On comparable top-100 subsets, effective half-spread sign and Kyle-lambda sign frequently change when feed-inferred direction is replaced with on-chain direction.

Primary research source:
- Philipp D. Dubach, `The Anatomy of a Decentralized Prediction Market: Microstructure Evidence from the Polymarket Order Book`, arXiv:2604.24366, 2026-04-27: https://arxiv.org/abs/2604.24366

Research consequence:
- Any Polymarket informed-flow, signed-volume, aggressor-side, effective-spread or price-impact experiment must use on-chain OrderFilled direction where the claim depends on trade sign, or explicitly remain `MEASUREMENT_UNPROVEN`.
- Public CLOB/WebSocket trade-side inference alone is not accepted as execution/microstructure ground truth.
- This is a measurement guardrail, not an edge.

Pre-Build Killer:
- Novelty in this KB: no matching prior record found for the on-chain-vs-feed direction validity gate.
- Semantic/data relevance: strong for microstructure/informed-flow research.
- Economic headroom: none by itself; no strategy warranted.

Chief Falsifier:
1. Source: academic paper, not venue documentation; treat numerical estimates as dataset/window-specific rather than universal constants.
2. Data: result is based on a large tick-level/on-chain join, but this run did not independently reproduce the archive.
3. Execution: measurement correction can prevent false positives but supplies no executable cashflow by itself.

Decision: KEEP_AS_GUARDRAIL / NO_PROVEN_EDGE.

## FX-DATA-001 — ForecastEx exposes free public intraday/daily CSV research data

Status: FACT_VERIFIED_OFFICIAL / DATA_SOURCE_CANDIDATE
Roles: scout, algebra, settlement, microstructure

ForecastEx's official Data page states that it provides public CSV files for event contracts, including `Pairs` data refreshed every 10 minutes, daily closing prices, and daily product/activity summaries. This creates a zero-cost source for broad ForecastEx census/history research without requiring a paid dataset.

Official source:
- https://forecastex.com/data (checked 2026-09-20)

Research consequence:
- Add this source to future source-registry work for ForecastEx structural/coupon-adjusted identity discovery.
- Ten-minute refresh is useful for slow structural screening and historical census, but is not contemporaneous L2 and cannot prove executable edge, queue/fill, or short-lived arbitrage.
- Existing negative evidence remains: same-market YES+NO coupon farming is closed by offsetting/accounting rules and observed combined asks; the existence of public CSV data does not reopen that route.

Pre-Build Killer:
- Novelty in this KB: no matching public-CSV source record found.
- Cheap empirical utility: high for venue census and slow structural discovery.
- Execution evidence: insufficient by construction.

Chief Falsifier:
1. Source: official ForecastEx page passes provenance.
2. Data: refresh cadence and file fields need schema/point-in-time validation before any experiment.
3. Execution: 10-minute files are not executable order-book evidence.

Decision: KEEP_AS_DATA_SOURCE / NO_PROVEN_EDGE.

## Discovery-only lead not promoted — domain calibration

A February 2026 paper using 292M trades across Kalshi and Polymarket reports domain/horizon calibration structure and a Kalshi-specific trade-size effect that does not replicate on Polymarket. Source: https://arxiv.org/abs/2602.19520. This is potentially relevant to behavioral research, but no execution-realistic rule, point-in-time replication, or independent confirmation was produced in this run. Keep as discovery lead only; do not create a candidate from the headline result.
