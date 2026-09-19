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
8. Geef niet op na één mislukte methode. Als een hypothese materieel interessant blijft, test haar waar praktisch mogelijk vanuit minimaal drie onafhankelijke invalshoeken voordat zij definitief wordt verworpen of gepromoveerd.
9. Presenteer geen belangrijke conclusie voordat een drievoudige zelfcontrole is uitgevoerd.

## Drievoudige zelfcontrole vóór conclusies

Voor iedere belangrijke claim, candidate edge of go/no-go-conclusie controleert de agent minimaal drie keer, bij voorkeur met verschillende failure modes:

1. **Semantiek / broncontrole** — Kloppen contracttekst, settlementregels, timestamps, units, definities, venue-documentatie en provenance werkelijk?
2. **Data / reproduceerbaarheid** — Kan dezelfde uitkomst opnieuw worden berekend uit point-in-time data zonder lookahead, verborgen aannames of handmatige selectie achteraf?
3. **Economische / execution-controle** — Overleeft de claim executable bid/ask, L2 depth, fees, slippage, partial fills, latency, collateral, settlement/finality en relevante operationele risico's?

Waar mogelijk moet een tweede onafhankelijke implementatie, query, dataset, bron of rekenroute één van deze controles dupliceren. Als drie controles niet mogelijk zijn, documenteer expliciet welke ontbreken en waarom.

## Drie-hoekenregel voor hypotheses

Test materiële hypotheses waar mogelijk vanuit minimaal drie verschillende hoeken. Voorbeelden:

- formele/logische payoff-analyse;
- historische execution-realistische replay;
- prospectieve shadow/canary observatie;
- alternatieve dataset of onafhankelijke bron;
- adversarial falsificatietest / counterexample search;
- station/market/regime/time-split out-of-sample test;
- onafhankelijke implementatie van dezelfde berekening.

De drie tests mogen niet slechts drie varianten van exact dezelfde aanname zijn. Het doel is verschillende failure modes af te dekken.

## Anti-fabricatie — absolute regel

- Nooit resultaten, fills, prijzen, orderbookdiepte, settlements, timestamps, backtests, screenshots, bronnen, statistische significantie of live-P&L verzinnen, aanpassen of selectief presenteren.
- Nooit tests achteraf versoepelen om een hypothese groen te krijgen.
- Nooit mislukte experimenten verwijderen omdat zij de thesis verzwakken.
- Nooit lookahead-data, gereviseerde data of informatie die pas na market close beschikbaar kwam behandelen alsof die point-in-time beschikbaar was.
- Onzekerheid, ontbrekende data en `UNKNOWN` moeten expliciet worden opgeslagen.
- Een onbewezen edge blijft `NO_PROVEN_EDGE`, hoe aantrekkelijk het mechanisme ook lijkt.

## Schrijfdiscipline

- Gebruik stabiele IDs per record.
- Voorkom dubbele IDs; maak bij revisie bijvoorbeeld `KAL-X-001-v2` of leg een expliciete `supersedes`-relatie vast.
- Citeer private bronrepo's met `repo/ref/path`, maar kopieer geen secrets/accountdetails naar deze publieke repo.
- Voor actuele online research: primaire bron > paper > betrouwbare secundaire bron > community.
- Communityclaims zijn `ANECDOTAL` totdat onafhankelijk bevestigd.
- Leg bij een nieuwe candidate meteen `falsification`, `required_data` en `execution_blockers` vast.
- Bewaar zowel positieve als negatieve resultaten zodat andere agents dezelfde doodlopende route niet opnieuw hoeven te ontdekken.

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
- probabilistische calibration gaps;
- onverwachte interacties tussen meerdere van bovenstaande mechanismen.

## Grens

Onderzoek mag agressief en creatief zijn, maar blijft binnen wet, toepasselijke platformregels en veilige researchgrenzen. Geen operationele research of uitvoering voor fraude, marktmanipulatie, misleiding, KYC-/geo-omzeiling, sabotage, credentialmisbruik of software-exploitatie. Publiek bekende securityproblemen mogen als negative evidence / execution risk worden vastgelegd zonder misbruikinstructies.

## Einddoel en bewijsstandaard

Het uiteindelijke doel is niet een mooie backtest maar een **reproduceerbare, structureel winstgevende methode die execution-realistisch standhoudt en uiteindelijk met echt geld prospectief kan worden gevalideerd**.

De volgorde blijft:

`hypothese → formele/empirische checks → historische replay → validation → untouched holdout → prospectieve shadow → micro-live met echt geld → herhaalde live-validatie`

Een live trade of één winstgevende dag bewijst geen structurele edge. Promotie naar `PROVEN_EDGE` vereist herhaalbare netto winst na alle relevante kosten en risico's, zonder dat regels of criteria achteraf zijn aangepast.

Het doel is een reproduceerbare edge te vinden **of** overtuigend vast te stellen dat een lane geen edge heeft. Beide zijn succesvolle researchuitkomsten; `NO_PROVEN_EDGE` blijft altijd een geldige conclusie.
