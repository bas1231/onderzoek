# FEX conditional-contract product family — 2026-09-22

Status: `FACT_VERIFIED_PRODUCT_EXISTENCE / STRUCTURAL_LEAD / NO_PROVEN_EDGE`

## Observatie
De publieke CFTC DCM-productfilings tonen drie nieuwe FEX-eventcontractfamilies, alle gecertificeerd op 2026-09-18 als binary-option swaps:

- `CPI-Fed Conditional Forecast Contract`
- `Unemployment-Recession Conditional Forecast Contract`
- `Senate Majority-US 500 Conditional Forecast Contract`

Primaire provenance: CFTC, Designated Contract Market Products, FEX, geraadpleegd 2026-09-22.

## Inferentie
Dit is een nieuwe productfamilie die expliciet conditionele relaties tussen twee gebeurtenissen/variabelen encodeert. Voor de Market Algebra / cross-venue research is dat interessanter dan een gewone losse binary, omdat er mogelijk formele relaties bestaan met de onderliggende marginale FEX-contracten of met semantisch equivalente contracten op andere venues.

Dit is uitsluitend een structural lead. Productcertificering bewijst niet dat de contracten actief/liquide zijn, dat hun settlementsemantiek exact aansluit op bestaande marginals, of dat een synthetische replicatie economisch goedkoper is.

## Specialist — ALGEBRA
Volgende beslissende vraag: wat is de exacte payoff/conditioning-semantiek van elk contract en kan die zonder aannames als toestandfunctie worden uitgeschreven naast de relevante marginale FEX-contracten?

Pas daarna vergelijken:
1. exacte settlement source/version/condition;
2. coupon/collateral accounting;
3. contemporaneous executable bid/ask en depth;
4. fees, slippage, partial-fill en capital lock.

## Red-team / cheap kill
Niet bouwen of prijzen op basis van de productnaam. `conditional` kan verschillende noemer-, void-, DNP-, coupon- of settlementbranches hebben. Een schijnbare identity zonder rulebook-proof is ongeldig. Zelfs een formele identity is geen edge zonder gelijktijdige executable prijs/depth.

## Economische conclusie
`NO_PROVEN_EDGE`.
