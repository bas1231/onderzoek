# Polymarket NegRisk V2 conversion semantics — 2026-09-22

Status: `FACT_VERIFIED / MECHANISM_REFINEMENT / NO_PROVEN_EDGE`
Candidate: `PM-NR-V2-CONVERT-001`

## Nieuwe primaire evidence

De actuele officiële `Polymarket/ctf-exchange-v2` implementatie maakt de V2 conversion-route expliciet. `NegRiskCtfCollateralAdapter.convertPositions()`:

1. leest `questionCount` en event-specifieke `feeBips` uit de legacy NegRiskAdapter;
2. trekt `_amount` NO-posities voor de indices in `_indexSet` naar de V2 collateral adapter;
3. roept de legacy `adapter.convertPositions()` aan;
4. stuurt voor de complementaire YES-posities niet `_amount`, maar `amountOut = _amount - (_amount * feeBips / 10_000)` terug naar de caller;
5. wrapt iedere door de legacy conversion ontvangen USDC.e naar de V2 `CollateralToken` (PMCT) en stuurt die naar de caller.

De V2 adapter is dus geen nieuwe losstaande NegRisk payoff-semantiek: hij composeert de legacy NegRisk conversion met de V2 collateral-laag. De conversion fee raakt expliciet de hoeveelheid complementaire YES die de V2 caller ontvangt; de collateral-return loopt via USDC.e -> PMCT.

## Betekenis voor de algebra-engine

Een V2 conversion mag niet worden gemodelleerd als alleen `m NO -> (m-1) collateral + full-size complement YES`. Voor een event met `feeBips > 0` moet de actuele adapterroute worden gemodelleerd met de fee-reduced complement-YES output en met de juiste collateral denomination/unwrap-route. Event-specifieke `feeBips` is daarom verplichte point-in-time provenance vóór een economische vergelijking.

Dit is een mechanisme-correctie, geen edge. Er is nog geen synchronized executable CLOB-depth bewijs, geen positieve fee/gas/depth-adjusted lower bound en geen execution proof.

## Falsificatie / guardrail

- Oude V1/legacy documentatie alleen is onvoldoende om V2 cashflows te prijzen.
- `feeBips == 0` mag niet worden aangenomen; lees het event-specifiek.
- PMCT/USDC.e accounting en eventuele onramp/offramp-frictie moeten expliciet blijven.
- Een payout-equivalent portfolio zonder point-in-time executable books blijft `NO_PROVEN_EDGE`.

## Provenance

Primaire bron, geraadpleegd 2026-09-22:
- `Polymarket/ctf-exchange-v2`, `src/adapters/NegRiskCtfCollateralAdapter.sol`, actuele `main`: `convertPositions()` en collateral wrapping.
- `Polymarket/neg-risk-ctf-adapter`, officiële `NegRiskAdapter` documentatie voor de onderliggende legacy conversionsemantiek.

Economische conclusie: `NO_PROVEN_EDGE`.
