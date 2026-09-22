# ForecastEx conditional contracts — cashflow semantics

Datum: 2026-09-22
Status: `FACT_VERIFIED / STRUCTURAL_LEAD / NO_PROVEN_EDGE`
Bronklasse: official_primary

## Nieuwe primaire evidence

CFTC filing 61812 voor ForecastEx `Fed-CPI Conditional Forecast Contract` (ZFFCP), self-certified 2026-07-16:
https://www.cftc.gov/IndustryOversight/IndustryFilings/TradingOrganizationProducts/61812
PDF:
https://www.cftc.gov/filings/ptc/ptc07162610667.pdf

De CFTC productlijst toont daarnaast drie nieuwe FEX conditional families, certified 2026-09-18: `CPI-Fed Conditional Forecast Contract`, `Unemployment-Recession Conditional Forecast Contract` en `Senate Majority-US 500 Conditional Forecast Contract`.

## Geobserveerde semantiek uit ZFFCP

1. De Conditioning Event wordt eerst geëvalueerd.
2. Alleen wanneer die event optreedt, wordt de Settlement Event geëvalueerd en volgt uiteindelijk een normale $1/$0 YES/NO payoff.
3. Wanneer de Conditioning Event niet optreedt, eindigt het contract zonder YES/NO-resolution. Uitstaande contracten worden dan afgerekend tegen de consideration die de houder betaalde om ze te verwerven. Daardoor ontstaat op het contract zelf geen winst of verlies in die branch; eerder betaalde transactiekosten worden niet terugbetaald.
4. Bij succesvolle conditioning kunnen posities operationeel worden omgezet naar de corresponderende unconditional Settlement Event-contracten, in dezelfde hoeveelheid en met dezelfde acquisition cost basis, zonder directe P/L-realisatie of settlement payment.
5. Conditional contracts zijn vóór resolution van de Conditioning Event niet eligible voor netting. Na succesvolle overgang naar de Settlement Event gelden de normale offset/nettingregels weer.
6. Forecast Contracts verdienen volgens de filing een maandelijkse incentive coupon op basis van daily settlement value; coupon/carry moet daarom afzonderlijk in economische vergelijkingen worden meegenomen.
7. Resolution kan worden vertraagd door source delays, schedule changes of event review; capital-lock/finality blijft een aparte executionvariabele.

## Algebraïsche consequentie

Een FEX conditional contract mag niet als simpele state-onafhankelijke binary payofffunctie `1[A and B]` of als directe `P(B|A)`-token worden gemodelleerd. De `not A`-branch retourneert de individuele acquisition consideration en verliest transactiekosten. De gerealiseerde cashflow is daardoor mede afhankelijk van de positie/acquisition basis en fee/coupon/capital-lock accounting.

Voor een formele identity of direct-vs-synthetic vergelijking moet de state engine minimaal modelleren:

- conditioning-event final resolution;
- settlement-event payoff;
- acquisition consideration per positie/lot;
- non-refundable transaction fees;
- pre-conditioning netting restriction;
- incentive coupon/carry;
- transition naar unconditional settlement contract;
- resolution/finality/capital-lock timing.

## Red-team / anti-false-positive

`Conditional` in de productnaam is geen bewijs voor een standaard conditionele kansclaim. Zelfs wanneer de logical event relation klopt, kan een statische payoff-identity fout zijn doordat de conditioning-failure branch cost-basis-dependent is. Een theoretische identity is bovendien nog geen economische edge zonder point-in-time executable bid/ask, depth, fees en capital-lock.

## Nieuwe researchvraag

Semantics-first vervolgstap: verkrijg de filings/terms voor één van de 2026-09-18 families en controleer of dezelfde refund-at-consideration, no-netting en couponstructuur daar letterlijk geldt. Pas daarna mag een concrete joint/marginal synthetic relation worden geformuleerd en execution-realistisch geprijsd.

Economische conclusie: `NO_PROVEN_EDGE`.
