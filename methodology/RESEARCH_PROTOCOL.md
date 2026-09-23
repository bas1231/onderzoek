# Research protocol

## Doel

Deze knowledge base moet venue-onafhankelijke discovery versnellen zonder hindsight, overfitting, multiple-testing zelfbedrog of execution-fantasie te introduceren.

Lees daarnaast `methodology/CONTINUOUS_PREDICTION_MARKET_RED_TEAM.md` voor de overkoepelende continuous-red-team architectuur.

## Positieve-EV scope en schaalbeleid

De research heeft **geen minimum dagwinst, minimum absolute dollarwinst of minimum winst per episode als toelatingsdrempel**.

- Iedere kandidaat die na relevante fricties en risico's aantoonbaar `net EV > 0` kan hebben, is onderzoekswaardig, ook wanneer de verwachte winst slechts centen per episode is.
- `€100+/dag` is een **uiteindelijke portfolio-schaalambitie**, geen eis voor een individuele candidate en geen kill-gate.
- Capacity, opportunity frequency, capital lock, capital efficiency, settlementhorizon en absolute dagwinst worden gemeten om candidates te **rangschikken en te schalen**, niet om een anders geldige kleine positieve edge automatisch weg te gooien.
- Een kleine edge mag uitsluitend wegens schaal lager worden geprioriteerd; zij blijft bewaard en onderzoekbaar zolang de netto EV positief kan zijn en execution realistisch blijft.
- Meerdere onafhankelijke kleine positieve edges mogen als portfolio worden gecombineerd. De som van kleine reproduceerbare edges is een geldige route naar het uiteindelijke schaaldoel.
- Een candidate wordt niet gekilled omdat zij “te weinig per dag” verdient. Kill/park vereist inhoudelijke reden, zoals falsificatie, `net EV <= 0`, non-executability, onaanvaardbaar risico/legaliteitsprobleem, ontbrekende bewijsbaarheid of expliciet gedocumenteerde opportunity cost.

Deze regel verlaagt **niet** de bewijsstandaard. Een kleine edge moet dezelfde point-in-time, execution-, validation- en anti-overfittinggates doorlopen als een grote edge.

## WATCH, parkeren en heropenen

`WATCH` is een **persistente niet-terminale monitoringstatus**. Het betekent niet dat een edge bewezen is, maar ook niet dat de route is afgewezen.

Gebruik `WATCH` wanneer een mechanisme of route nu onvoldoende bewijs, economics, toegang, liquidity of actualiteit heeft om actief te promoveren, maar door **materieel nieuwe informatie** later opnieuw relevant kan worden.

Iedere WATCH-entry legt waar mogelijk vast:

- `watch_reason`: waarom nu geen actieve promotie plaatsvindt;
- `recheck_triggers`: concrete omstandigheden die herbeoordeling rechtvaardigen;
- `preserved_negative_evidence`: welke eerdere negatives/failure modes geldig blijven;
- `last_checked_at` en relevante provenance;
- `current_status`: bijvoorbeeld `WATCH`, `RECHECK_TRIGGERED`, `ACTIVE_RESEARCH`, `TESTED_NEGATIVE`;
- `candidate_refs`/`mechanism_refs` zodat nieuws aan bestaande research wordt gekoppeld in plaats van als nieuw idee te worden gedupliceerd.

Geldige recheck-triggers zijn onder meer:

- wijziging van contractregels, settlementbron, rounding/finality of oracle;
- fee-, rebate-, reward-, collateral- of incentivewijziging;
- gewijzigde venue-/jurisdictie-/participanttoegang;
- nieuw executionpad zoals RFQ, block trading, nieuwe routering of nieuwe ordertypes;
- materiële verandering in spread, L2-depth, volume, queue/fill-gedrag of opportunity lifetime;
- nieuwe primaire bron, academische/mechanistische evidence of nieuwe dataset;
- een vooraf vastgelegde nieuwe holdout of prospectieve observation die een eerder probleem rechtstreeks test;
- een concrete nieuwe contractpair/market instance die een eerder formeel mechanisme opnieuw testbaar maakt.

Een trigger **promoveert nooit automatisch**. Hij zet de route op `RECHECK_TRIGGERED`; daarna gelden opnieuw semantiek-, data-, execution-, falsificatie- en validatiegates.

Eerdere negatieve evidence wordt nooit gewist. Een WATCH-resurrection moet expliciet aangeven **welke beslissende dependency is veranderd**. Zonder zo'n verandering wordt een oude gefalsificeerde variant niet eindeloos opnieuw getest.

Voorbeeld: een estimator die op developmentdata is gefalsificeerd wordt niet opnieuw getuned op dezelfde data omdat er toevallig nieuw nieuws is; alleen orthogonale methode, nieuwe preregistratie of nieuwe untouched/holdout evidence kan die route inhoudelijk heropenen.

## Bewijslagen

### 0. Pre-build viability
Voordat nieuwe strategy- of infrastructurecode wordt gebouwd: novelty/negative evidence, semantic viability, economic headroom, goedkope empirische falsificatie en execution spotcheck. Alleen survivors krijgen normaal een build warrant. Lage absolute winst alleen is geen reden om een otherwise plausibele positive-EV survivor uit te sluiten; engineeringprioriteit mag wel op informatiewaarde en opportunity cost worden gerangschikt.

### 1. Semantic / rules proof
Leg exact vast wat het contract betaalt in iedere toegestane toestand. Titelgelijkenis is alleen discovery. Source, measurement window, threshold, rounding, revision, DNP/cancel/void/fair-price, oracle en finality kunnen de payoff veranderen.

### 2. Signal edge
Voor probabilistische strategieën: voorspelt het model de uiteindelijke relevante settlementwaarde/outcome out-of-sample beter dan sterke baselines?

### 3. Market edge
Bevat de actuele executable marktprijs die informatie al? Een beter voorspellend model zonder verbetering tegenover de markt is geen tradingstrategie.

### 4. Execution proof
Gebruik gelijktijdige point-in-time bid/ask/L2, echte side/direction, depth, fees, collateral/capital lock, queue/fill assumptions, partial-fill/legging, latency en settlement/finality. UI 'chance', midpoint, last trade en stale mirrors zijn geen executionbewijs.

## Vereiste validatievolgorde

1. pre-build kill gates;
2. unit/invariant/regression;
3. vooraf gedefinieerde historische execution-realistische replay;
4. development;
5. validation;
6. volledig untouched holdout;
7. prospectieve live-canary/shadow;
8. alleen bij standhoudende edge: afzonderlijk geautoriseerde micro-live test.

Tests of aannames worden niet achteraf aangepast om een idee groen te krijgen. Een materiële hypothesewijziging creëert een nieuw experiment op nieuwe untouched data.

## Adaptive search / multiple hypotheses

Een systeem dat veel hypotheses test moet de search zelf als bron van bias behandelen.

Minimaal:

- registreer hypothesis family/search family;
- registreer hoeveel relevante subgroups/parameterizations zijn bekeken;
- post-hoc subgroup discoveries worden nieuwe hypotheses;
- gebruik waar passend vooraf gedefinieerde alpha/FDR-regels, sequential testing, e-values of andere geldige error-control methoden;
- gebruik dezelfde holdout niet herhaaldelijk als developmentfeedback;
- een mooie nominale p-waarde zonder search-context is geen promotiebewijs.

## Correlatie en meetunit

Buckets/thresholds/combo's van dezelfde settlement zijn niet onafhankelijk. Cluster minimaal op de economische onderliggende gebeurtenis. Voor venue-/cross-venue relaties moet de independence unit expliciet worden gedefinieerd; meerdere quotes/polls/fills van dezelfde episode zijn niet automatisch onafhankelijke kansen.

## Data trust / point in time

Iedere kernbron moet waar relevant vastleggen:

- source authority;
- source timestamp;
- collector receipt timestamp;
- clock uncertainty;
- sequence integrity;
- revision/backfill policy;
- direction/maker-taker authority;
- completeness en missingness;
- historische reconstruction quality.

Als een feed een veld/semantiek niet betrouwbaar bewijst, mag die betekenis niet worden aangenomen.

## Knowledge-record minimum

Iedere duurzame claim/hypothese hoort waar mogelijk deze velden te hebben:

```yaml
id: UNIQUE-ID
venue: kalshi|polymarket|forecastex|cross_venue|other
mechanism_id: optional
kind: fact|observation|hypothesis|negative_evidence|candidate
status: FACT_VERIFIED|OBSERVED|HYPOTHESIS_UNTESTED|TESTED_NEGATIVE|STRUCTURAL_CANDIDATE|RESEARCH_POSITIVE|WATCH|RECHECK_TRIGGERED|EXECUTION_BLOCKED|NO_PROVEN_EDGE
claim: "..."
as_of: YYYY-MM-DD
source_class: PRIMARY|PAPER|SECONDARY|COMMUNITY|DARK_MARKET_INTELLIGENCE
search_family: optional
multiple_testing_context: optional
watch_reason: optional
recheck_triggers: []
preserved_negative_evidence: []
provenance: []
required_data: []
falsification: []
execution_blockers: []
related: []
```

## Provenance

- Primaire regels/documentatie hebben voorrang op blogs en communityclaims.
- Communitymateriaal mag hypotheses/tests genereren maar is geen proof.
- Een point-in-time observatie wordt niet automatisch gegeneraliseerd.
- Latere brondata mag ontbrekende historische evidence niet reconstrueren.
- Schema-/transportfouten en negatieve runs blijven bewaard.
- Dark-market intelligence wordt apart gelabeld en kan nooit op zichzelf execution autoriseren.

## Veiligheid / legaliteit

In scope: legale marktinefficiëntie, contractalgebra, settlement/finality, fees/collateral, cross-venue semantics, probabilistische miscalibratie, maker/taker-flow, behavioral bias, openbaar gedocumenteerde protocolmechanismen en legaal grijze/onbedoelde economische mechanismen.

`ILLEGAL = HARD STOP` voor uitvoering.

Niet in scope: manipulatie, wash trading, spoofing, fraude, misleiding, credentialmisbruik, sabotage, ongeautoriseerde toegang, of operationeel misbruik van software/security-kwetsbaarheden. Securityinformatie kan defensief worden opgeslagen als intelligence/negative evidence/execution risk.

Dark-web/illicit markets mogen uitsluitend als intelligencebron worden meegenomen via rechtmatig beschikbare publieke/academische/forensische bronnen; geen operationele deelname of handel.

## Economische standaard

Totdat alle relevante gates zijn gepasseerd blijft de economische status:

`NO_PROVEN_EDGE`

Wanneer een edge uiteindelijk wordt bewezen, is **positieve netto EV** de economische kernvoorwaarde; er geldt geen afzonderlijke minimum-dagwinst om haar als echte edge te erkennen. Schaal en materialiteit worden daarna als aparte portfolio- en prioriteitsdimensies gerapporteerd.
