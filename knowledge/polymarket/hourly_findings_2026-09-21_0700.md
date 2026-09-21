# Polymarket hourly finding — 2026-09-21 07:00 CEST

Status: **RESEARCH_POSITIVE (measurement guardrail) / NO_PROVEN_EDGE**

## Nieuwe evidence

Een publieke academische microstructure-paper (Dubach, arXiv:2604.24366) koppelt een continue Polymarket WebSocket-orderbookarchive (ca. 30 miljard events over 52 dagen) aan de authoritative on-chain trade record. Op een preregistreerd panel van 600 markten rapporteert de auteur dat trade direction afgeleid uit de publieke orderbookfeed slechts ongeveer 59% overeenkomt met on-chain ground truth (panel mean 0.615, 95% CI [0.58, 0.65]). In twee niet-overlappende windows wisselde het teken van effective half-spread op veel markten wanneer feed-inferred versus on-chain direction werd gebruikt; ook Kyle's lambda kon van teken wisselen.

Een tweede publieke paper (Nechepurenko, arXiv:2605.11640) documenteert een structurele attribution-beperking: Polymarket OrderPlaced en OrderCancelled zijn off-chain en ontbreken uit publieke on-chain archives. Daardoor zijn address-level quote-lifecycle claims (quote intensity, posted spread, two-sided ratio en spoof-by-non-fill attribution) niet betrouwbaar uit alleen on-chain fills te reconstrueren. De paper trekt zulke address-level market-making claims daarom expliciet terug.

## Routing

### microstructure

Nieuwe harde measurement guardrail: gebruik voor Polymarket trade-side/direction analyses waar richting economisch relevant is authoritative on-chain `OrderFilled` evidence, niet alleen feed-inferred direction. Een bookfeed blijft nuttig voor contemporaneous depth/quotes, maar is geen betrouwbare ground truth voor aggressor/trade direction.

### informed_flow

Address-level informed-flow of maker-archetype claims mogen niet stilzwijgend worden afgeleid uit fill-only/on-chain data wanneer de hypothese quote placement/cancellation gedrag vereist. De ontbrekende off-chain quote lifecycle is dan een structural identifiability blocker. Market-level book diagnostics en fill-side signatures blijven mogelijk, maar moeten als zodanig worden gelabeld.

### behavioral / algebra / settlement / weather_twc

Geen nieuwe economische uitkomst.

## Pre-Build Killer

Geen strategy-build. Dit is een data-validity finding, geen positieve edge. Een strategie die voordeel claimt uit inferred aggressor side, maker identity of cancellation behavior faalt de cheap evidence gate wanneer de benodigde provenance ontbreekt.

## Chief Falsifier

Drie failure modes:

1. **Semantiek/provenance:** feed-side inference kan trade direction verkeerd labelen.
2. **Data/identifiability:** off-chain OrderPlaced/OrderCancelled ontbreken in on-chain archives, dus address-level quote lifecycle is niet observeerbaar uit fills alleen.
3. **Economisch/execution:** zelfs correcte fill-side classificatie bewijst geen executable edge; fees, contemporaneous depth, fill probability, adverse selection en capital lock blijven vereist.

## Independent Reproducer

Niet geactiveerd: er is geen positieve economische instance. Voor toekomstige serieuze Polymarket microstructure/informed-flow candidates wordt onafhankelijke on-chain/feed reconciliation onderdeel van de validation gate.

## Besluit

Duurzame nieuwe guardrail, geen candidate-promotie. Economische status blijft **NO_PROVEN_EDGE**.

## Bronnen

- Philipp D. Dubach, *The Anatomy of a Decentralized Prediction Market: Microstructure Evidence from the Polymarket Order Book*, arXiv:2604.24366 (2026).
- Maksym Nechepurenko, *Fill-Side Non-Retail Trading on Polymarket: An Empirical Study of Behavioral Tiers and Microstructure Signatures Under Quote-Attribution Constraints*, arXiv:2605.11640 (2026).
