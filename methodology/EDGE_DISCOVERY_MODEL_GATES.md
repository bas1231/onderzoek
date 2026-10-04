# Prediction Model Gates & Edge Objective

Status: **NORMATIVE**
Datum: 2026-10-04

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

## 3. Verplichte modelrollen

De research lifecycle gebruikt de volgende rolverdeling.

### Director / researcher

De bestaande reasoning-worker analyseert candidates en bepaalt de eerstvolgende beslissende falsificatie. Een advies `NEEDS_BUILD` of `VALIDATION` is **geen autorisatie** om direct verder te gaan.

### Astra pre-build gate

Voordat code/tooling voor een kansrijke hypothese mag worden gebouwd, moet **GPT-6 Astra** de exact gebonden candidate-versie onafhankelijk beoordelen.

State:

`ASTRA_PREBUILD_REVIEW`

Alleen een review met:

- `reviewer_model = GPT-6 Astra`;
- exact passende binding-hash;
- `decision = APPROVE`;
- `ANY_POSITIVE_NET_EDGE_COUNTS`;
- alle safety flags false;

mag de state naar `NEEDS_BUILD` brengen.

Een stale review of review van een ander model is ongeldig.

### Builder

Bouwen gebeurt volgens:

`required_builder_policy = HIGHEST_AVAILABLE_GPT`

De builder bevriest objective/scope/acceptance criteria en voert relevante compile-, unit-, integration-, regression- en canary/shadow-tests uit.

Build evidence vermeldt de gebruikte builder en:

`builder_policy = HIGHEST_AVAILABLE_GPT`

Een technische build-PASS is nooit automatisch bewijs van economische edge.

### Astra pre-measurement gate

Na build/tests en vóór code prospectief op actuele marktdata gaat meten, beoordeelt **GPT-6 Astra** opnieuw de exact gebonden versie.

State:

`ASTRA_PREMEASUREMENT_REVIEW`

Alleen Astra-APPROVE kan:

`MEASUREMENT_READY`

opleveren.

## 4. Betekenis van "live meten"

Binnen dit protocol betekent een measurement deployment:

`READ_ONLY_PROSPECTIVE_MARKET_DATA`

Dit is **geen live trading**.

Toegestaan binnen de automatische researchketen:

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

De safety flags blijven daarom:

- `live_trading = false`
- `paid_actions = false`
- `wallet_actions = false`

## 5. Volledige gewenste keten

```text
Scout
  -> persistent candidate
  -> Director / falsification
  -> ASTRA_PREBUILD_REVIEW
  -> hoogste beschikbare GPT bouwt
  -> technische tests / deathchecks / canary
  -> Director beoordeelt build-resultaat
  -> ASTRA_PREMEASUREMENT_REVIEW
  -> hoogste beschikbare GPT deployt read-only/shadow meting
  -> prospectieve actuele marktdata
  -> immutable measurement evidence
  -> Director / falsifier / reproducer
  -> netto economisch oordeel
       -> NO_PROVEN_EDGE / REJECT / PARK
       -> of verdere proof gates bij positieve survivor
  -> rapportage
```

## 6. Binding en fail-closed gedrag

Astra-review is versiegebonden aan candidate, evidence en relevante Director/validation-hashes. Iedere materiële wijziging maakt een eerdere approval ongeldig.

Legacy of handmatig geschreven `NEEDS_BUILD` / `VALIDATION` mag de gate niet omzeilen. De runtime migreert of blokkeert zulke states totdat de vereiste Astra-review bestaat.

De build-wake, fixed-validator selector en measurement-wake voeren zelf eveneens gatecontroles uit zodat een directe interne call de router-gate niet kan omzeilen.

## 7. Einddoel

Succes is niet "veel ideeën" en ook niet "grote theoretische percentages".

Succes is het vinden van één of meer **reproduceerbare, netto positieve, execution-realistische mechanisms** die uiteindelijk geld kunnen verdienen — ook wanneer de absolute winst in eerste instantie klein is.
