# Polymarket — resolution, protocol finality en redemption zijn aparte toestanden

Datum: 2026-09-21
Status: `FACT_VERIFIED / RESEARCH_CONTEXT / NO_PROVEN_EDGE`

## Nieuwe evidence
Twee op 14 september 2026 gepubliceerde papers van Maksym Nechepurenko reconstrueren de Polymarket/UMA/CTF lifecycle event-sourced en ondersteunen een voor dit project belangrijke scheiding:

`contractuele beslisbaarheid -> oracle request/proposal/dispute/reset -> oracle finality -> adapter/protocol settlement -> holder redemption`

Part I bevriest een populatie van 185.550 adapter-question instances en rapporteert 184.148 request creations, 159.447 proposals, 1.604 disputes en 159.133 settlements. Een economische vraag kan meerdere request generations krijgen na resets. Bovendien werden 1.570 rule updates gevonden; 83,34% van 1.711 exact gekoppelde clarification-generation relaties lag na request creation maar vóór first proposal. Een request timestamp is dus geen betrouwbare proxy voor het moment waarop een contract semantisch beslisbaar was.

Part II koppelt 108.638 CTF conditions exact; 99.283 hadden bij de bevroren snapshot een protocol-resolution event. Van de exact gekoppelde resolved conditions hadden 92.158 een waargenomen redemption van enig bedrag en 91.817 een positieve payout redemption. De gerapporteerde medianen vanaf eerste protocol resolution waren respectievelijk 182 en 200 seconden. De auteurs benadrukken terecht dat een redemption event zonder entitlement-denominator niet bewijst welk deel van de aanspraak is gerealiseerd.

## Research-OS implicatie
Voor settlement/algebra/capital-lock onderzoek mag één veld `resolved_at` niet als voldoende state worden gebruikt. Candidate- en replaymodellen moeten waar relevant minimaal onderscheiden:

- rule/clarification version en contractuele beslisbaarheid;
- request generation en predecessor/successor na reset;
- proposal/dispute/oracle-finality;
- adapter/CTF protocol-finality;
- redeemability en waargenomen holder redemption;
- capital-lockduur per laag.

Voor `PM-NR-V2-CONVERT-001` betekent dit dat terminal payoff-equivalentie en conversion support nog steeds onvoldoende zijn voor economics: settlement-only legs moeten de protocol-finality/capital-lock route expliciet meenemen. Dit versterkt de reeds bestaande execution-first regel en is geen kandidaatpromotie.

## Falsificatie / grenzen
- De papers meten population-wide external-source publication en contractuele beslisbaarheid niet; mechanisme-timestamps mogen die clocks niet vervangen.
- Observed redemption is geen volledige entitlement-accounting.
- Historische lifecycle-statistieken bewijzen geen huidige executable arbitrage.
- Geen contemporaneous L2, fees, gas, depth of synchronized conversion portfolio is in deze finding geleverd.

## Provenance
- arXiv:2609.15368 — *Resolution Is Not Settlement, Part I: Oracle Adjudication and Semantic Governance on Polymarket*, 2026-09-14.
- arXiv:2609.15373 — *Resolution Is Not Settlement, Part II: Protocol Finality and Observed Redemption on Polymarket*, 2026-09-14.

Economische conclusie: `NO_PROVEN_EDGE`.
