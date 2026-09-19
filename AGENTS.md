# AGENTS.md — Prediction Market Research KB

Deze repository is een gedeelde kennislaag waarop meerdere AI-sessies/agents parallel mogen schrijven.

## Bij iedere researchtaak

1. Lees eerst `README.md`, `methodology/RESEARCH_PROTOCOL.md` en `negative_evidence/LEDGER.md`.
2. Zoek bestaande records voordat je een nieuwe hypothese als nieuw presenteert.
3. Voeg nieuwe informatie toe met datum, status en provenance.
4. Bewaar conflicterend bewijs naast elkaar; overschrijf het niet met een samengevoegde conclusie.
5. Verander `NO_PROVEN_EDGE` alleen wanneer de vereiste signal/market/execution/validation gates expliciet zijn gehaald.
6. Een geslaagde technische of semantische gate is `RESEARCH_POSITIVE`, niet automatisch economische edge.
7. Een gefalsificeerde route blijft bestaan en krijgt `TESTED_NEGATIVE`; nooit verwijderen om de knowledge base optimistischer te maken.

## Schrijfdiscipline

- Gebruik stabiele IDs per record.
- Voorkom dubbele IDs; maak bij revisie bijvoorbeeld `KAL-X-001-v2` of leg een explicit supersedes-relatie vast.
- Citeer private bronrepo's met `repo/ref/path`, maar kopieer geen secrets/accountdetails naar deze publieke repo.
- Voor actuele online research: primaire bron > paper > betrouwbare secundaire bron > community.
- Communityclaims zijn `ANECDOTAL` totdat onafhankelijk bevestigd.
- Leg bij een nieuwe candidate meteen falsification/required_data/execution_blockers vast.

## Discovery

Agents mogen onder meer zoeken naar:
- payout/contract identities en dominance;
- source/finality/settlement lag;
- cross-venue semantic relations;
- combos/MVE/subset/superset algebra;
- scalar/DNP/void/fair-price branches;
- fees/collateral/reward/carry overlays;
- maker/taker/adverse-selection/flowbias;
- forecast revision, regime en information-lag;
- queue/depth/latency/partial-fill effecten;
- probabilistische calibration gaps.

## Grens

Geen operationele research voor fraude, manipulatie, KYC-/geo-omzeiling, sabotage, credentialmisbruik of software-exploitatie. Publiek bekende securityproblemen mogen als negative evidence / execution risk worden vastgelegd zonder misbruikinstructies.

## Resultaat

Het doel is een reproduceerbare edge te vinden **of** overtuigend vast te stellen dat een lane geen edge heeft. Beide zijn succesvolle researchuitkomsten.
