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

> **MANDATORY ACCEPTANCE CRITERION — TARGET ARCHITECTURE**
>
> De vereiste lifecycle is exact:
>
> `Scout -> selectie -> GPT-5.6 Sol-opzet -> GPT-6 Astra pre-build review -> GPT-5.6 Sol-build -> GPT-6 Astra post-build code-review -> tests en meting -> supervisor -> rapportage over EDGE / NO_EDGE / NO_PROVEN_EDGE`
>
> **Astra beoordeelt dus verplicht vóór én na de build.**
>
> Bij iedere Astra-afkeur of `NEEDS_REVISION` verwerkt Sol de feedback, maakt een nieuwe exact gebonden versie en biedt die opnieuw aan Astra aan. **Tests en metingen van het edge-experiment mogen pas starten nadat exact GPT-6 Astra de daadwerkelijk gebouwde code/harness expliciet heeft goedgekeurd.**
>
> Een implementatie, testfixture of A→Z-kwalificatie die deze volgorde omdraait of tests/meting vóór de post-build Astra-approval laat starten, **voldoet niet aan de canonical acceptance criteria** en mag niet als volledige A→Z-PASS worden gerapporteerd.

### Uitvoeringslaag — Sol direct, Astra via Codex

De modelrol en de uitvoeringslaag zijn afzonderlijke begrippen.

Voor nieuwe governed runs geldt:

- `SOL_PROPOSAL` en `SOL_BUILD`: exact **GPT-5.6 Sol via DIRECT_SOL**, buiten Codex;
- `ASTRA_PREBUILD`, `ASTRA_POSTBUILD` en Astra-supervisorreviews: exact **GPT-6 Astra via CODEX_WORKER**.

De directe Sol-route moet exact `gpt-5.6-sol` afdwingen, zonder modeltools, met `store=false` en met exacte prompt/completion-provenance. Astra blijft bewust op een andere uitvoeringslaag om de onafhankelijke reviewrol te behouden.

De migratie verandert geen enkele wetenschappelijke gate. `NO_TEST_OR_MEASUREMENT_BEFORE_ASTRA_POSTBUILD_APPROVAL` blijft ongewijzigd.

Zie `control/model_execution/ROUTING.md`.

### Director / researcher

De bestaande reasoning-worker analyseert candidates, selecteert kansrijke hypotheses en bepaalt de eerstvolgende beslissende falsificatie. Een advies `NEEDS_BUILD` of `VALIDATION` is **geen autorisatie** om direct een experiment te bouwen, testen of meten.

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

Voordat het daadwerkelijke edge-experiment mag worden gebouwd, moet **exact GPT-6 Astra** de exact gebonden Sol-opzet onafhankelijk beoordelen.

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

Tijdens de build zijn alleen bouwgerichte checks toegestaan die nodig zijn om een reviewbaar artefact te produceren, zoals syntax/import/compile checks. **De inhoudelijke experimenttests, validatieruns, backtests, shadowmetingen of andere edge-metingen starten nog niet.**

Een technische build-PASS is nooit automatisch bewijs van economische edge en geeft op zichzelf geen toestemming om te testen of meten.

### GPT-6 Astra — verplichte post-build code-review en feedbacklus

Na de Sol-build, maar **vóór iedere inhoudelijke test of meting**, beoordeelt **exact GPT-6 Astra** de daadwerkelijk gebouwde, exact gebonden code/harness.

Canonical state:

`ASTRA_POSTBUILD_REVIEW`

Astra beoordeelt minimaal:

- of de gebouwde code de eerder goedgekeurde Sol-opzet correct implementeert;
- of objective, scope en falsificatiecriteria onveranderd zijn gebleven;
- of data- en tijdsafbakening correct zijn;
- of leakage/look-ahead/bias technisch wordt voorkomen;
- of meet- en scoringslogica klopt;
- of execution-realistische kosten/fills/slippage correct zijn geïmplementeerd waar relevant;
- of de test- en meetpaden reproduceerbaar en fail-closed zijn;
- of safetygrenzen en read-only/shadow-beperkingen technisch worden afgedwongen;
- of de exacte code/harness-hashes overeenkomen met de reviewbinding.

Alleen een geldige, exact gebonden:

`decision = APPROVE`

mag de lifecycle vrijgeven naar tests en meting.

Bij `NEEDS_REVISION` of afkeur:

1. Astra-feedback gaat versiegebonden terug naar GPT-5.6 Sol;
2. Sol verwerkt de feedback en bouwt een nieuwe versie;
3. de nieuwe build krijgt nieuwe hashes/binding;
4. **er worden nog steeds geen inhoudelijke tests of metingen uitgevoerd**;
5. exact GPT-6 Astra beoordeelt de nieuwe gebouwde versie opnieuw;
6. deze lus herhaalt zich totdat Astra `APPROVE` geeft of de kandidaat wordt afgewezen/geparkeerd.

Een Astra-approval van buildversie N is ongeldig voor buildversie N+1.

### Tests en meting — uitsluitend na Astra post-build approval

Pas nadat `ASTRA_POSTBUILD_REVIEW = APPROVE` voor de actuele build is vastgelegd, mag het experiment technisch/invaliderend worden getest en volgens de goedgekeurde opzet worden uitgevoerd/gemeten.

Daaronder vallen onder meer:

- unit/integratie-/acceptatietests van de experimentlogica;
- frozen-fixture en positive-control tests;
- replay/backtest/holdout;
- prospectieve shadowmeting;
- andere inhoudelijke validatie die economische of wetenschappelijke evidence produceert.

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

### Supervisor — beoordeling na tests en meting

Na tests en meting beoordeelt de supervisor/falsifier/reproducer de immutable evidence en bepaalt of het bewijs leidt tot:

- `EDGE`;
- `NO_EDGE`;
- `NO_PROVEN_EDGE`;
- aanvullende proof/reproduction gates;
- of afwijzen/parkeren.

De supervisor mag een ontbrekende pre-build of post-build Astra-approval nooit achteraf repareren of overslaan. Als de actuele build niet vóór tests/meting door exact GPT-6 Astra was goedgekeurd, is de run voor volledige A→Z-acceptance ongeldig en moet hij fail-closed worden geclassificeerd.

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
       -> NEEDS_REVISION: feedback -> Sol reviseert opzet -> opnieuw Astra
       -> REJECT/PARK: stop
       -> APPROVE: door
  -> GPT-5.6 Sol bouwt daadwerkelijk edge-experiment
  -> ASTRA_POSTBUILD_REVIEW (exact GPT-6 Astra) op de gebouwde code/harness
       -> NEEDS_REVISION: feedback -> Sol herbouwt -> opnieuw Astra
       -> REJECT/PARK: stop
       -> APPROVE: pas nu vrijgave voor tests/meting
  -> technische/invaliderende tests
  -> experiment uitvoeren en meten
  -> immutable measurement evidence
  -> Director / falsifier / reproducer / supervisor
  -> netto economisch oordeel
       -> NO_PROVEN_EDGE / NO_EDGE / REJECT / PARK
       -> of verdere proof gates bij positieve survivor
  -> rapportage
```

Canonical shorthand:

`Scout -> selectie -> Sol-opzet -> Astra pre-build review/revisielus -> Sol-build -> Astra post-build code-review/revisielus -> tests en meting -> supervisor -> rapportage`

Hard sequencing invariant:

`NO_TEST_OR_MEASUREMENT_BEFORE_ASTRA_POSTBUILD_APPROVAL`

Dit is een formeel acceptatiecriterium. Een A→Z-test die tests of meting uitvoert vóór de post-build Astra-approval is per definitie **geen geldige volledige A→Z-PASS**, ook als alle latere stappen technisch groen zijn.

## 6. Wetenschappelijke default

`NO_PROVEN_EDGE` blijft de default totdat de vereiste bewijs- en reviewgates aantoonbaar zijn gehaald.

Een correcte experimentbuild kan eindigen in:

`BUILD_PASS + NO_PROVEN_EDGE`

Dat is een geldige onderzoeksuitkomst.

Een lagere technische PASS, een enkele positieve meting of alleen een Astra pre-build approval promoveert nooit automatisch naar bewezen economische edge.

## 7. Einddoel

Succes is niet "veel ideeën" en ook niet "grote theoretische percentages".

Succes is het vinden van één of meer **reproduceerbare, netto positieve, execution-realistische mechanisms** die uiteindelijk geld kunnen verdienen — ook wanneer de absolute winst in eerste instantie klein is — via een lifecycle waarin Sol de opzet maakt en bouwt, exact GPT-6 Astra zowel vóór de build als na de build de actuele versie onafhankelijk goedkeurt, en pas daarna tests/meting, supervisorbeoordeling en rapportage plaatsvinden.
