# Kalshi fractional trading / variable price-grid guardrail — 2026-09-21 10:00 CEST

Status: **FACT_VERIFIED / METHODOLOGY_GUARDRAIL / NO_PROVEN_EDGE**

## Nieuwe evidence

De actuele officiële Kalshi Trade API-documentatie voor multivariate events exposeert per nested market onder meer `fractional_trading_enabled`, `price_level_structure` en `price_ranges` met `start`, `end` en `step`. Dezelfde market payload gebruikt daarnaast fixed-point/dollarvelden zoals `yes_bid_dollars`, `yes_bid_size_fp`, `volume_fp`, `open_interest_fp` en `settlement_value_dollars`.

Bron: Kalshi API Documentation, `GET /events/multivariate`, publiek geraadpleegd 2026-09-21.

## Betekenis

Dit is geen economische edge. Het is een execution/algebra guardrail: tooling mag niet universeel aannemen dat ieder Kalshi-contract alleen gehele contractaantallen of een uniforme 1-cent prijsgrid gebruikt. Per-market quantity- en price-grid semantics moeten point-in-time uit de venue-metadata worden vastgelegd en bij replay/orderbook/algebra worden toegepast.

## Specialist-routing

- scout: nieuwe machineleesbare productschema-evidence.
- microstructure: tick/grid en fractional-size semantics horen bij executable-price/depth normalisatie.
- algebra: portfolio quantities en kosten moeten de actuele market precision respecteren; afronding naar oude integer/cents-aannames kan false positives of false negatives veroorzaken.
- settlement: geen nieuwe settlementclaim; `settlement_value_dollars` bevestigt alleen dat settlementwaarde als expliciet veld bestaat.
- weather_twc / behavioral / informed_flow: geen nieuwe uitkomst.

## Pre-Build Killer

Geen strategy-build. Dit verandert bewijsdiscipline, niet economische headroom.

## Chief Falsifier

Iedere kandidaat die een Kalshi-price/quantity-grid hardcodeert moet worden aangevallen op: (1) actuele `price_level_structure`/`price_ranges`, (2) `fractional_trading_enabled`, en (3) fixed-point versus legacy integer parsing. Zonder point-in-time schema-evidence geen execution-proof.

## Economische conclusie

Signal edge: niet bewezen. Market edge: niet bewezen. Execution edge: niet bewezen.

**NO_PROVEN_EDGE**
