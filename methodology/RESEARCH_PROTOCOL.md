# Research protocol

## Doel

Deze knowledge base moet venue-onafhankelijke discovery versnellen zonder hindsight, overfitting, multiple-testing zelfbedrog of execution-fantasie te introduceren.

Lees daarnaast `methodology/CONTINUOUS_PREDICTION_MARKET_RED_TEAM.md` voor de overkoepelende continuous-red-team architectuur.

## Bewijslagen

### 0. Pre-build viability
Voordat nieuwe strategy- of infrastructurecode wordt gebouwd: novelty/negative evidence, semantic viability, economic headroom, goedkope empirische falsificatie en execution spotcheck. Alleen survivors krijgen normaal een build warrant.

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
status: FACT_VERIFIED|OBSERVED|HYPOTHESIS_UNTESTED|TESTED_NEGATIVE|STRUCTURAL_CANDIDATE|RESEARCH_POSITIVE|EXECUTION_BLOCKED|NO_PROVEN_EDGE
claim: "..."
as_of: YYYY-MM-DD
source_class: PRIMARY|PAPER|SECONDARY|COMMUNITY|DARK_MARKET_INTELLIGENCE
search_family: optional
multiple_testing_context: optional
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
