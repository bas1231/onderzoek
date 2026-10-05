# Prediction Model Gates & Edge Objective

Status: **NORMATIVE**
Datum: 2026-10-05

## 1. Economisch doel

Het research-systeem heeft als doel **reproduceerbare, uitvoerbare prediction-market edges te vinden die netto geld kunnen verdienen**.

Er geldt **geen minimale winstdrempel in euro's** voor onderzoek:

- iedere strikt positieve netto verwachte/opgemeten opbrengst is relevant;
- ook een reproduceerbare edge van centen of enkele euro's mag niet worden afgewezen omdat het bedrag klein is;
- omvang beïnvloedt hooguit prioritering/capitaal-efficiëntie, niet de vraag of een valide hypothese getest moet worden.

Canonical policy:

`ANY_POSITIVE_NET_EDGE_COUNTS`

met:

`minimum_net_profit_eur = 0.0`

Een bruto voordeel telt niet als edge. Netto beoordeling houdt minimaal rekening met toepasselijke fees, spread/slippage, fill probability/partial fills, limieten, kapitaalbeslag en relevante operationele kosten.

## 2. Bewijs blijft streng

"Alles testen" betekent niet "alles geloven".

Een enkele positieve observatie, backtest of toevallige fill bewijst geen edge. `NO_PROVEN_EDGE` blijft de standaard totdat relevante gates zijn gehaald, waaronder waar toepasselijk:

- correcte contract/settlement-semantiek;
- vooraf vastgelegde hypothese en falsificatie;
- geen hindsight/post-close leakage;
- lokale technische tests;
- prospectieve/out-of-sample observaties;
- execution-realistische kosten/fills/slippage;
- voldoende herhaling/sample;
- onafhankelijke reproduction/review waar vereist.

Een kleine maar echte edge is valide. Een grote maar niet-reproduceerbare paper edge is dat niet.

## 3. Verplichte modelrollen en reviewlus

De research lifecycle gebruikt de volgende vaste rolverdeling.

### Director / researcher

De bestaande reasoning-worker analyseert candidates, selecteert kansrijke hypotheses en bepaalt de eerstvolgende beslissende falsificatie. Een advies `NEEDS_BUILD` of `VALIDATION` is **geen autorisatie** om direct een experiment te bouwen of uit te voeren.

### GPT-5.6 Sol — experimentele opzet

Voor een kandidaat die de eerste selectie passeert maakt **GPT-5.6 Sol** eerst een concrete, versiegebonden experimentele opzet. Dit is nog niet de definitieve uitvoering van het edge-experiment.

De opzet bevat minimaal:

- hypothese;
- falsificatiecriterium;
- benodigde data en tijdsafbakening;
- point-in-time/replay/backtest/holdout/shadow-methodiek waar van toepassing;
- mogelijke leakage/look-ahead/bias;
- meet- en scoringslogica;
- execution-realistische kosten/fills/slippage waar relevant;
- succes- en faalcriteria;
- reproduceerbaarheidsplan.

### GPT-6 Astra — pre-build review en feedbacklus

Voordat het daadwerkelijke edge-experiment mag worden gebouwd of uitgevoerd, moet **exact GPT-6 Astra** de exact gebonden Sol-opzet onafhankelijk beoordelen.

State:

`ASTRA_PREBUILD_REVIEW`

Alleen een review met:

- `reviewer_model = GPT-6 Astra`;
- exact passende binding-hash;
- geldige autonome model-provenance;
- `decision = APPROVE`;
- `ANY_POSITIVE_NET_EDGE_COUNTS`;
- alle safety flags false;

mag de kandidaat doorzetten naar daadwerkelijke experimentbouw.

Bij `NEEDS_REVISION` of inhoudelijke afkeur:

1. Astra-feedback wordt versiegebonden teruggegeven aan GPT-5.6 Sol;
2. Sol verwerkt die feedback in een nieuwe opzetversie;
3. de nieuwe versie krijgt een nieuwe binding;
4. exact GPT-6 Astra beoordeelt die nieuwe versie opnieuw;
5. de lus herhaalt zich totdat Astra expliciet `APPROVE` geeft of de kandidaat definitief wordt afgewezen/geparkeerd.

Een approval voor versie N geldt nooit automatisch voor versie N+1.

Modelidentiteit wordt **niet** bewezen door zelfverklaring in modeltekst. Voor productie moet Astra autonoom door de uitvoeringslaag worden geselecteerd. De werkelijk gebruikte modelslug/modelversie wordt als run-provenance vastgelegd en cryptografisch gebonden aan review, candidate en experiment-opzet.

Een handmatig geopende Astra-chat met sessieroute-attestation is uitsluitend toegestaan voor expliciet gemarkeerde systeemkwalificatie-fixtures (`qualification_fixture=true`). Zulke provenance draagt `usage_scope=TEST_ONLY` en faalt gesloten voor productie-candidates.

Ontbrekende, gewijzigde, ingetrokken of niet-autonome production-provenance blokkeert de gate.

### GPT-5.6 Sol — daadwerkelijke experimentbouw

Na geldige Astra pre-build approval bouwt **GPT-5.6 Sol** het daadwerkelijke experiment waarmee de candidate op mogelijke edge wordt onderzocht.

Canonical policy:

`required_experiment_builder_model = GPT-5.6 Sol`

Dit experiment kan afhankelijk van de hypothese bestaan uit bijvoorbeeld:

- point-in-time replay;
- backtest;
- historische simulatie;
- dataverwerking/featureberekening;
- hypothesetest;
- holdout-evaluatie;
- shadow-test;
- meet- en scoringslogica;
- andere reproduceerbare experimentele harness.

Sol bevriest objective/scope/acceptance criteria en bouwt tegen de door Astra goedgekeurde opzet. De build evidence vermeldt minimaal de exacte builder-provenance, candidate/opzetversie en relevante hashes.

Een technische build-PASS is nooit automatisch bewijs van economische edge.

### Uitvoering, tests en meting

Het door Sol gebouwde experiment wordt daadwerkelijk technisch getest en daarna volgens de goedgekeurde opzet uitgevoerd/gemeten.

Waar actuele marktdata wordt gebruikt, blijft dit:

`READ_ONLY_PROSPECTIVE_MARKET_DATA`

Dit is **geen live trading**.

Toegestaan:

- actuele publieke marktdata lezen;
- orderbooks/quotes/rules/resultaten observeren;
- shadow/paper fills modelleren;
- prospectieve signalen en kansen timestampen;
- immutable meetresultaten opslaan;
- netto edge achteraf volgens het vooraf vastgelegde protocol berekenen.

Niet toegestaan zonder afzonderlijke expliciete menselijke autorisatie:

- order submit;
- order cancel;
- geld inzetten;
- wallet/fund movement;
- betaalde API/dataset/cloudactie;
- micro-live of ander financieel handelen.

De safety flags blijven:

- `live_trading = false`
- `paid_actions = false`
- `wallet_actions = false`

### GPT-6 Astra — post-experiment review

Na technische tests, uitvoering en meting beoordeelt **exact GPT-6 Astra** opnieuw de exact gebonden gerealiseerde experimentversie en resultaten.

State:

`ASTRA_POSTEXPERIMENT_REVIEW`

Astra beoordeelt minimaal:

- of Sol daadwerkelijk de goedgekeurde opzet heeft geïmplementeerd;
- of de gerealiseerde code/harness bij de goedgekeurde versie hoort;
- data- en tijdsafbakening;
- leakage/look-ahead/bias;
- test- en meetmethodiek;
- execution-realistische aannames;
- resultaten en onzekerheid;
- reproduceerbaarheid;
- of de conclusie `EDGE`, `NO_EDGE` of `NO_PROVEN_EDGE` door het bewijs wordt gedragen.

Bij `NEEDS_REVISION` of afkeur:

1. Astra-feedback gaat versiegebonden terug naar GPT-5.6 Sol;
2. Sol past het experiment, de analyse of beide aan binnen de toegestane scope;
3. relevante technische tests/meting worden opnieuw uitgevoerd;
4. de nieuwe versie wordt opnieuw aan exact GPT-6 Astra aangeboden.

Pas na geldige post-experiment approval mag de lifecycle door naar definitieve supervisor/reproducer-beslissing en eindrapportage.

## 4. Versiebinding en fail-closed gedrag

Alle opzetten, reviews, builds, meetresultaten, approvals en autorisaties zijn exact versiegebonden.

Minimale invarianten:

- approval van versie N geldt niet voor N+1;
- een stale Astra-review is ongeldig;
- een stale meetautorisatie mag niet als actueel worden gerapporteerd;
- ontbrekende of foutieve model-provenance faalt gesloten;
- een verkeerde reviewer of builder faalt gesloten;
- een builder anders dan GPT-5.6 Sol mag de experimentbouw niet vrijgeven;
- iedere materiële wijziging na pre-build approval maakt de relevante eerdere approval ongeldig en vereist opnieuw de toepasselijke Astra-review;
- rapportage onderscheidt historische van actuele approvals;
- legacy of handmatig geschreven `NEEDS_BUILD` / `VALIDATION` mag geen gate omzeilen.

De build-wake, validators/selectors, experiment-runner en rapportagelaag voeren zelf eveneens gatecontroles uit zodat directe interne calls de router-gates niet kunnen omzeilen.

## 5. Volledige gewenste keten

```text
Scout
  -> persistent candidate
  -> Director / eerste falsification-selectie
  -> GPT-5.6 Sol maakt versiegebonden experimentele opzet
  -> ASTRA_PREBUILD_REVIEW (exact GPT-6 Astra)
       -> NEEDS_REVISION: feedback -> Sol reviseert -> opnieuw Astra
       -> REJECT/PARK: stop
       -> APPROVE: door
  -> GPT-5.6 Sol bouwt daadwerkelijk edge-experiment
  -> technische tests / deathchecks / canary waar relevant
  -> experiment uitvoeren en meten
  -> immutable measurement evidence
  -> ASTRA_POSTEXPERIMENT_REVIEW (exact GPT-6 Astra)
       -> NEEDS_REVISION: feedback -> Sol repareert -> opnieuw testen/meten -> opnieuw Astra
       -> REJECT/PARK/NO_PROVEN_EDGE: vastleggen
       -> APPROVE: door
  -> Director / falsifier / reproducer / supervisor
  -> netto economisch oordeel
       -> NO_PROVEN_EDGE / REJECT / PARK
       -> of verdere proof gates bij positieve survivor
  -> rapportage
```

Canonical shorthand:

`Scout -> selectie -> Sol-opzet -> Astra pre-build review/revisielus -> Sol bouwt experiment -> test/uitvoering/meting -> Astra post-experiment review/revisielus -> supervisor -> rapportage`

## 6. Wetenschappelijke default

`NO_PROVEN_EDGE` blijft de default totdat de vereiste bewijs- en reviewgates aantoonbaar zijn gehaald.

Een correcte experimentbuild kan eindigen in:

`BUILD_PASS + NO_PROVEN_EDGE`

Dat is een geldige onderzoeksuitkomst.

Een lagere technische PASS, een enkele positieve meting of alleen een Astra pre-build approval promoveert nooit automatisch naar bewezen economische edge.

## 7. Einddoel

Succes is niet "veel ideeën" en ook niet "grote theoretische percentages".

Succes is het vinden van één of meer **reproduceerbare, netto positieve, execution-realistische mechanisms** die uiteindelijk geld kunnen verdienen — ook wanneer de absolute winst in eerste instantie klein is — via een lifecycle waarin Sol het experiment ontwerpt/bouwt en exact GPT-6 Astra onafhankelijk vóór en na de uitvoering reviewt.
