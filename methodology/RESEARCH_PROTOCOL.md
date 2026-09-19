# Research protocol

## Doel

Deze knowledge base moet discovery versnellen zonder hindsight, overfitting of execution-fantasie te introduceren.

## Bewijslagen

### 1. Semantic / rules proof
Leg exact vast wat het contract betaalt in iedere toegestane toestand. Titelgelijkenis is alleen discovery. Source, measurement window, threshold, rounding, revision, DNP/cancel/void/fair-price en finality kunnen de payoff veranderen.

### 2. Signal edge
Voor probabilistische strategieën: voorspelt het model de uiteindelijke relevante settlementwaarde/outcome out-of-sample beter dan sterke baselines?

### 3. Market edge
Bevat de actuele executable marktprijs die informatie al? Een beter voorspellend model zonder verbetering tegenover de markt is geen tradingstrategie.

### 4. Execution proof
Gebruik gelijktijdige point-in-time bid/ask/L2, echte side/direction, depth, fees, collateral, partial-fill/legging, latency en settlement/finality. UI 'chance', midpoint, last trade en stale mirrors zijn geen executionbewijs.

## Vereiste validatievolgorde

1. unit/invariant/regression;
2. vooraf gedefinieerde historische execution-realistische replay;
3. development;
4. validation;
5. volledig untouched holdout;
6. prospectieve live-canary/shadow;
7. alleen bij standhoudende edge: afzonderlijk geautoriseerde micro-live test.

Tests of aannames worden niet achteraf aangepast om een idee groen te krijgen. Een materiële hypothesewijziging creëert een nieuw experiment op nieuwe untouched data.

## Correlatie en meetunit

Buckets/thresholds/combo's van dezelfde settlement zijn niet onafhankelijk. Cluster minimaal op de economische onderliggende gebeurtenis; bij sport-state-lock ook op game + beslissend score-event + contractscope.

## Knowledge-record minimum

Iedere duurzame claim/hypothese hoort waar mogelijk deze velden te hebben:

```yaml
id: UNIQUE-ID
venue: kalshi
kind: fact|observation|hypothesis|negative_evidence|candidate
status: FACT_VERIFIED|OBSERVED|HYPOTHESIS_UNTESTED|TESTED_NEGATIVE|STRUCTURAL_CANDIDATE|RESEARCH_POSITIVE|NO_PROVEN_EDGE
claim: "..."
as_of: YYYY-MM-DD
provenance:
  - repo: owner/repo
    ref: branch-or-commit
    path: path/to/file
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

## Veiligheid / legaliteit

In scope: legale marktinefficiëntie, contractalgebra, settlement/finality, fees/collateral, cross-venue semantics, probabilistische miscalibratie, maker/taker-flow en openbaar gedocumenteerde protocolmechanismen.

Niet in scope: manipulatie, wash trading, spoofing, fraude, KYC-/geo-omzeiling, credentialmisbruik, sabotage, front-running via ongeoorloofde toegang of operationeel misbruik van software/security-kwetsbaarheden. Securityinformatie kan defensief worden opgeslagen als reden waarom een theoretische strategie niet proof-safe is.

## Economische standaard

Totdat alle relevante gates zijn gepasseerd blijft de economische status:

`NO_PROVEN_EDGE`
