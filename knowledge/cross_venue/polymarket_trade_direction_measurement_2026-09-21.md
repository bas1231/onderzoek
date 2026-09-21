# Polymarket trade-direction measurement risk — 2026-09-21

Status: **DURABLE NEGATIVE / MEASUREMENT CAUTION / NO_PROVEN_EDGE**

## Bron

Publieke academische preprint: Philipp D. Dubach, *The Anatomy of a Decentralized Prediction Market: Microstructure Evidence from the Polymarket Order Book*, arXiv:2604.24366 (2026). De paper gebruikt een tick-level archief van de publieke Polymarket WebSocket orderbook-feed en koppelt dit aan de authoritatieve on-chain `OrderFilled`-records.

Bron-URL: https://arxiv.org/abs/2604.24366

## Nieuwe duurzame finding

De paper rapporteert dat trade direction afgeleid uit de publieke orderbook-feed slechts ongeveer 59% overeenkomt met on-chain ground truth (panel mean 0.615; 95% CI [0.58, 0.65]). Op een vergelijkbare top-100 subset veranderde zelfs het teken van effective half-spread tussen feed-afgeleide en on-chain trade direction op 67% van de markten in een eerste 7-daags venster en 50% in een tweede niet-overlappend venster; Kyle's lambda flipte respectievelijk op 60% en 43%.

Dit is geen trading edge. Het is methodologische negative evidence: informed-flow, adverse-selection en maker/taker analyses op Polymarket mogen trade direction niet als betrouwbaar behandelen wanneer die uitsluitend uit de publieke orderbook-feed wordt geïnferreerd. Waar direction essentieel is, is een join naar on-chain `OrderFilled` evidence vereist of moet de richting als `UNKNOWN` blijven.

## Routing

- `microstructure`: materieel; execution/markout-statistieken kunnen van teken veranderen bij verkeerde direction labeling.
- `informed_flow`: materieel; flow imbalance en informed-flow signatures zijn niet valide als aggressor direction uit de feed wordt gegist.
- `behavioral`: indirect; direction-dependent behavioral claims moeten dezelfde caution erven.
- `algebra`: geen nieuwe payout identity.
- `settlement`: geen nieuwe settlementsemantiek.
- `weather_twc`: geen directe weather/KWI finding.

## Pre-Build Killer

**PASS als data-quality kill rule; FAIL als strategy-build warrant.** De finding bespaart engineering op flowstrategieën die op onbetrouwbare feed-direction steunen, maar levert zelf geen executable mispricing, payout guarantee of economische headroom.

## Chief Falsifier

Belangrijkste failure modes voor gebruik van deze paper:

1. venue/regime drift: de gemeten 52-daagse sample hoeft niet ieder toekomstig regime te representeren;
2. direction mismatch is een measurement result, geen bewijs dat alle feedvelden onbetrouwbaar zijn;
3. on-chain join kan eigen timestamp/join ambiguïteiten hebben en moet bij lokale reproductie expliciet worden gecontroleerd;
4. de paper bewijst geen winstgevende informed-flow strategie, alleen dat een veelgebruikte measurement shortcut zwak is.

## Independent Reproducer

Niet geactiveerd: er is geen economische survivor. Als later een Polymarket flow-candidate direction-sensitive blijkt, moet een kleine onafhankelijke feed↔`OrderFilled` reproduction vóór promotie worden uitgevoerd.

## Economische conclusie

Signal edge: niet aangetoond.
Market edge: niet aangetoond.
Execution edge: niet aangetoond.

**NO_PROVEN_EDGE**.
