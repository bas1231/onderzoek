# AGENTS.md — Prediction Market Research KB

Deze repository is een gedeelde kennislaag waarop meerdere AI-sessies/agents parallel mogen schrijven.

## Bij iedere researchtaak

1. Lees eerst `README.md`, `methodology/CONTINUOUS_PREDICTION_MARKET_RED_TEAM.md`, `methodology/RESEARCH_PROTOCOL.md`, `methodology/EXECUTION_FIRST_DISCOVERY.md` en `negative_evidence/LEDGER.md`.
2. Zoek bestaande records voordat je een nieuwe hypothese als nieuw presenteert.
3. Voeg nieuwe informatie toe met datum, status en provenance.
4. Bewaar conflicterend bewijs naast elkaar; overschrijf het niet met een samengevoegde conclusie.
5. Verander `NO_PROVEN_EDGE` alleen wanneer de vereiste signal/market/execution/validation gates expliciet zijn gehaald.
6. Een geslaagde technische of semantische gate is `RESEARCH_POSITIVE`, niet automatisch economische edge.
7. Een gefalsificeerde route blijft bestaan en krijgt `TESTED_NEGATIVE`; nooit verwijderen om de knowledge base optimistischer te maken.
8. Geef niet op na één mislukte methode. Als een hypothese materieel interessant blijft, test haar waar praktisch mogelijk vanuit minimaal drie onafhankelijke invalshoeken voordat zij definitief wordt verworpen of gepromoveerd.
9. Presenteer geen belangrijke conclusie voordat een drievoudige zelfcontrole is uitgevoerd.
10. Zoek bij voorkeur **execution-first**: prioriteer constructies waarvan de netto cashflow werkelijk kan worden vastgelegd boven losse prijsafwijkingen, midpoint-curl of theoretische mispricing.
11. Behandel de researchscope als **venue-onafhankelijk**. Kalshi is één venue, niet de defaultgrens.
12. Nieuwe strategycode vereist normaal een pre-build warrant: novelty, semantics, economic headroom, cheap empirical evidence en execution spotcheck moeten voldoende sterk zijn om nieuwe engineering te rechtvaardigen.
13. Registreer bij grootschalige discovery expliciet hoeveel hypotheses/subgroups/parameterizations zijn getest; voorkom dat adaptive search als onafhankelijke bevestiging wordt gepresenteerd.

## Drievoudige zelfcontrole vóór conclusies

Voor iedere belangrijke claim, candidate edge of go/no-go-conclusie controleert de agent minimaal drie keer, bij voorkeur met verschillende failure modes:

1. **Semantiek / broncontrole** — Kloppen contracttekst, settlementregels, timestamps, units, definities, venue-documentatie en provenance werkelijk?
2. **Data / reproduceerbaarheid** — Kan dezelfde uitkomst opnieuw worden berekend uit point-in-time data zonder lookahead, verborgen aannames, multiple-testing artefact of handmatige selectie achteraf?
3. **Economische / execution-controle** — Overleeft de claim executable bid/ask, L2 depth, fees, slippage, queue/fill assumptions, partial fills, latency, collateral/capital lock, settlement/finality en relevante operationele risico's?

Waar mogelijk moet een tweede onafhankelijke implementatie, query, dataset, bron of rekenroute één van deze controles dupliceren. Als drie controles niet mogelijk zijn, documenteer expliciet welke ontbreken en waarom.

## Vijf verbeteringsreviews voor plannen/methodologie

Een materiële architectuur- of methodologywijziging wordt waar praktisch mogelijk vanuit vijf hoeken herzien:

1. **Waste review** — kan het idee eerder/goedkoper worden gedood voordat nieuwe code nodig is?
2. **False-positive review** — welke leakage, dependence, adaptive-search of multiple-testing route kan ons misleiden?
3. **Execution review** — welke fill/queue/latency/depth/settlement/capital assumption is te gunstig?
4. **Transfer review** — welke kennis hoort venue-agnostisch als mechanisme in de knowledge graph?
5. **Adversarial-source review** — welke source/clock/revision/feed/on-chain/off-chain/provenance assumption kan fout, stale of incompleet zijn?

## Execution-first discovery

De primaire economische vraag is niet alleen of prijzen afwijken, maar:

> Welke positie of portfolio kan **nu daadwerkelijk worden geconstrueerd**, wat betaalt die in iedere toegestane settlementstate, en blijft de conservatieve netto cashflow positief na alle relevante fricties?

Agents behandelen een anomaly, midpoint-dislocatie, modelmispricing of synthetisch/direct verschil alleen als discovery-signaal. Voor promotie moet waar relevant expliciet worden berekend:

- settlement/payoff per leg;
- exacte koop-/verkooprichting;
- simultane executable bid/ask;
- L2-depth en maximale werkelijk uitvoerbare quantity;
- fees;
- slippagebuffer;
- queue/fill assumptions;
- partial-fill/legging risk;
- latency/collateral/capital lock/finality;
- worst-case netto settlementcashflow.

Voorkeursmaat:

`net_locked_edge = worst_case_settlement_cashflow - executable_cost - fees - slippage_buffer - execution_risk_buffer`

Een kandidaat met een mooie theoretische afwijking maar `net_locked_edge <= 0` is geen economische edge. Ontbreekt voldoende point-in-time evidence voor de volledige constructie, dan blijft de status `UNKNOWN`, `STRUCTURAL_CANDIDATE`, `EXECUTION_BLOCKED` of `NO_PROVEN_EDGE`.

Zie `methodology/EXECUTION_FIRST_DISCOVERY.md` voor de volledige methodologische regel.

## Praktische infrastructuurconstraint

Onderzoek en ranking van kansen moeten passen bij de werkelijk beschikbare infrastructuur van de gebruiker:

- één krachtige **ROG Strix met Intel i9** en dus veel lokale rekenkracht voor parsing, algebra, optimalisatie, simulatie, replay, theorem proving en batch-search;
- snelle internetverbinding via **Starlink**, maar geen colocatie, dedicated exchange cross-connects, gespecialiseerde ultra-low-latency networking of professionele HFT-infrastructuur;
- ga daarom uit van normale retail-netwerklatency en jitter, niet van gegarandeerde microseconde- of colocatielatency.

Geef **lagere prioriteit** aan kansen die alleen realistisch zijn wanneer men consequent de markt op milliseconde-/microsecondeniveau moet verslaan, vooraan in een professionele queue moet staan of gespecialiseerde colocatie nodig heeft.

Geef **hogere prioriteit** aan kansen waarbij lokale rekenkracht wel een voordeel kan geven en waarbij de opportunity voldoende lang of structureel genoeg bestaat om via gewone snelle internetinfrastructuur uitvoerbaar te zijn, bijvoorbeeld:

- formele payout/cashflow identities;
- settlement/finality-structuur;
- synthetische versus directe portfolio's;
- exhaustive relation search;
- combinatorische/MVE/algebraïsche productrelaties;
- optimization/theorem-proving over grote contractuniversa;
- behavioral-flow inefficiënties met voldoende lifetime;
- kansen met voldoende marge en lifetime om fees, spreads, latency en fill-risico conservatief te overleven.

Een strategie die theoretisch winstgevend is maar alleen uitvoerbaar is met infrastructuur die de gebruiker niet heeft, wordt als `EXECUTION_BLOCKED`/`NO_PROVEN_EDGE` behandeld voor deze researchdoelstelling.

## Drie-hoekenregel voor hypotheses

Test materiële hypotheses waar mogelijk vanuit minimaal drie verschillende hoeken. Voorbeelden:

- formele/logische payoff-analyse;
- historische execution-realistische replay;
- prospectieve shadow/canary observatie;
- alternatieve dataset of onafhankelijke bron;
- adversarial falsificatietest / counterexample search;
- market/regime/time-split out-of-sample test;
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
- Voorkom dubbele IDs; maak bij revisie bijvoorbeeld `MECH-X-001-v2` of leg een expliciete `supersedes`-relatie vast.
- Citeer private bronrepo's met `repo/ref/path`, maar kopieer geen secrets/accountdetails naar deze publieke repo.
- Voor actuele online research: primaire bron > paper > betrouwbare secundaire bron > community.
- Communityclaims zijn `ANECDOTAL` totdat onafhankelijk bevestigd.
- Leg bij een nieuwe candidate meteen `falsification`, `required_data`, `execution_blockers`, `search_family` en waar relevant `multiple_testing_context` vast.
- Bewaar zowel positieve als negatieve resultaten zodat andere agents dezelfde doodlopende route niet opnieuw hoeven te ontdekken.
- Sla mechanismen waar mogelijk venue-onafhankelijk op en link venue-specifieke evidence eraan.

## Efficiencyregel voor antwoorden aan de gebruiker

Elk agent-antwoord aan de gebruiker bevat aan het einde een korte samenvatting van maximaal **5 regels**. Deze samenvatting moet alleen de belangrijkste uitkomst, status, blocker(s) en/of eerstvolgende relevante actie bevatten. Vermijd herhaling van details die al in het hoofdantwoord staan.

## Discovery

Agents mogen onder meer zoeken naar:
- payout/contract identities en dominance;
- source/finality/settlement lag;
- cross-venue semantic relations;
- combos/subset/superset/conditional algebra;
- scalar/DNP/void/fair-price branches;
- fees/collateral/reward/carry overlays;
- maker/taker/adverse-selection/flowbias;
- behavioral bias, framing, FOMO, herding, salience en partition effects;
- forecast revision, regime en information-lag;
- queue/depth/latency/partial-fill effecten;
- probabilistische calibration gaps;
- venue lifecycle/governance/oracle verschillen;
- onverwachte interacties tussen meerdere van bovenstaande mechanismen.

Discovery moet steeds worden terugvertaald naar de vraag of een **werkelijk uitvoerbare netto cashflow** kan worden geconstrueerd. Een interessante anomalie zonder zo'n pad krijgt lagere prioriteit dan een formeel payoutmechanisme met realistische execution.

## Dark-market intelligence

Dark-web/illicit markets mogen als **intelligencebron** in de knowledge base worden opgenomen wanneer de bron rechtmatig beschikbaar is, bijvoorbeeld via publieke academische datasets, forensische publicaties, threat-intelligence/OSINT of historische onderzoeksdata.

Doel is mechanismen, failures, governance, escrow/reputation, settlement, fraud/scam patterns en overdraagbare hypothesen te leren kennen en die waar mogelijk op legale prediction markets te testen.

Dark/illicit markets zijn **geen execution-lane**: geen financiering, handel, aankoop/verkoop, facilitering of deelname aan illegale activiteit. Findings krijgen waar mogelijk `source_class: DARK_MARKET_INTELLIGENCE`.

## Grens

Onderzoek mag maximaal agressief en creatief zijn binnen legale researchgrenzen. **Legaal grijs, vreemd of onbedoeld is in scope; illegale uitvoering is een harde stop.** Geen operationele research of uitvoering voor fraude, marktmanipulatie, misleiding, sabotage, credentialmisbruik, ongeautoriseerde toegang of software-exploitatie. Publiek bekende securityproblemen mogen als negative evidence / intelligence / execution risk worden vastgelegd zonder misbruikinstructies.

## Einddoel en bewijsstandaard

Het uiteindelijke doel is niet een mooie backtest maar een **reproduceerbare, structureel winstgevende methode die execution-realistisch standhoudt en uiteindelijk met echt geld prospectief kan worden gevalideerd**, of overtuigend vaststellen dat een lane geen edge heeft.

De volgorde blijft:

`hypothese → pre-build kill gates → formele/empirische checks → historische replay → validation → untouched holdout → prospectieve shadow → micro-live met echt geld → herhaalde live-validatie`

Een live trade of één winstgevende dag bewijst geen structurele edge. Promotie naar `PROVEN_EDGE` vereist herhaalbare netto winst na alle relevante kosten en risico's, zonder dat regels of criteria achteraf zijn aangepast.

`NO_PROVEN_EDGE` blijft altijd een geldige en gewenste onderzoeksuitkomst.

## Lokale autonome uitvoering

Wanneer onderzoek via de lokale WSL control-plane wordt uitgevoerd,
gelden aanvullend de regels in `control/LOCAL_EXECUTION_RULES.md`.

De lokale executor is een research-worker en geen live-trading executor.
