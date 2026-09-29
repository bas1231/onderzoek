# PvA — Sol Builder / Astra Reviewer

**Task-ID:** ARCH-SOL-BUILDER-ASTRA-REVIEWER-20260929  
**Intelligence tier:** Tier A  
**Status:** PLANNED — NOT YET IMPLEMENTED OR ACCEPTED  
**Scientific default:** `NO_PROVEN_EDGE`  
**Date:** 2026-09-29

## 1. Doel

Herstel de autonome build-capaciteit zonder de onafhankelijke Tier-A-controle te verliezen.

Beoogde scheiding:

```
Sol -> builder
deterministische tests/gates -> mechanische verificatie
Astra -> onafhankelijke Tier-A reviewer
CHANGES_REQUIRED -> terug naar Sol
PASS + alle gates groen -> acceptatie mogelijk
```

Dit document geeft geen toestemming voor live trading, wallet/crypto-acties, betaalde API's, andere kostdragende acties of het omzeilen van bestaande safety/provenance-guardrails.

## 2. Probleem

De eerdere architectuur maakte de hoogste-intelligentie reviewer tevens de feitelijke bouwroute. In combinatie met executor-, provenance- en no-push-beperkingen kan dit ertoe leiden dat research wel bevindingen oplevert maar noodzakelijke codewijzigingen niet autonoom worden gebouwd.

De oplossing mag niet zijn om review- of provenancecontroles te verwijderen. Builder en reviewer worden juist expliciet gescheiden.

## 3. Rollen

### 3.1 Sol — builder

Sol mag binnen een geautoriseerde build-taak:
- codewijzigingen ontwerpen en implementeren;
- tests toevoegen of aanpassen;
- bugs repareren;
- een door Astra gevraagde revisie implementeren;
- build-evidence, diff, testresultaten en provenance produceren.

Sol mag niet zelfstandig een Tier-A wijziging finaal accepteren.

### 3.2 Astra — onafhankelijke reviewer

Astra ontvangt de kandidaatwijziging pas nadat de builder-output en deterministische testresultaten beschikbaar zijn.

Astra geeft één van:
- `PASS`
- `CHANGES_REQUIRED`
- `BLOCKED_INSUFFICIENT_EVIDENCE`

Bij `CHANGES_REQUIRED` moet Astra minimaal vastleggen:
1. concreet bezwaar;
2. betrokken bestand/onderdeel/evidence;
3. waarom dit correctness, wetenschappelijke geldigheid, provenance, exact-once, veiligheid of toekomstige execution kan raken;
4. vereiste verbetering;
5. waar nuttig een concrete oplossingsrichting;
6. welke verificatie nodig is voor herreview.

Astra's voorstel is advies/review-output en wordt nooit rechtstreeks als uitvoerbare code behandeld.

### 3.3 Deterministische gates

LLM-output vervangt nooit:
- hashes/provenance;
- schema-validatie;
- evidence-cutoffcontrole;
- deduplicatie;
- exact-once/retry;
- state-machine-regels;
- queue/wake-regels;
- mechanische deathchecks;
- testresultaten.

Een Tier-A `PASS` is noodzakelijk maar niet voldoende: alle toepasselijke deterministische gates moeten eveneens slagen.

## 4. Revisielus

```
AUTHORIZED_BUILD_TASK
        |
        v
      SOL
   build Vn
        |
        v
deterministische tests
        |
   fail +------> SOL reviseert
        |
       pass
        v
      ASTRA
        |
  +-----+----------------------+
  |                            |
CHANGES_REQUIRED              PASS
  |                            |
  v                            v
SOL bouwt Vn+1       finale deterministic gates
  |                            |
  +---- tests -> ASTRA <-------+
                               |
                               v
                    ACCEPTABLE / BLOCKED
```

Iedere iteratie krijgt een duurzame identiteit zodat review van Vn niet per ongeluk Vn+1 kan goedkeuren.

## 5. Verplichte run-metadata

Per modelrun duurzaam vastleggen:
- task-id;
- intelligence-tier;
- rol: builder/reviewer;
- werkelijk gebruikt model;
- modelversie/slug indien beschikbaar;
- reasoningniveau;
- input-hash;
- candidate/diff-hash;
- parent iteration;
- start/eindtijd;
- resultaat/status.

Geen stille degradatie: als de vereiste Astra/Tier-A-reviewcapaciteit niet beschikbaar is, wordt de kandidaat `REQUIRES_HIGH_INTELLIGENCE_REVIEW` en niet finaal geaccepteerd.

## 6. Implementatiefasen

### Fase A — inventarisatie

Vind alle huidige plekken die builder/reviewer/modelkeuze afdwingen:
- supervisor;
- executor/preflight;
- policy/config;
- queue/task-schema;
- bridge/worker;
- provenance/installatie;
- tests en systemd-wakepaden.

Output: complete enforcement-map. Geen gedrag wijzigen.

### Fase B — rolcontract en schema

Voeg expliciete machineleesbare velden toe voor:
- `builder`;
- `reviewer`;
- `review_status`;
- `iteration_id`;
- `candidate_hash`;
- `reviewed_candidate_hash`.

Een review mag alleen gelden voor exact de kandidaat-hash die Astra werkelijk heeft beoordeeld.

### Fase C — Sol-buildroute

Maak Sol de builder voor geautoriseerde buildtaken.

Behoud:
- sandbox/isolation;
- capabilitygrenzen;
- no-live/no-cost defaults;
- provenance;
- bestaande owner intent;
- geen vrije uitvoering van modeltekst.

### Fase D — Astra-reviewroute

Na groene buildertests wordt een onafhankelijke Astra-reviewtaak gemaakt.

De reviewer krijgt:
- doel en Tier;
- diff/candidate;
- relevante tests;
- provenance;
- toepasselijke guardrails;
- eerdere review indien revisie.

Review-output wordt als data opgeslagen.

### Fase E — autonome revisielus

Bij `CHANGES_REQUIRED`:
- maak nieuwe Sol-revisietaak;
- geef bezwaren en vereiste verificatie mee;
- maak nieuwe iteration-id;
- voer tests opnieuw uit;
- stuur de nieuwe kandidaat opnieuw naar Astra.

Geen oneindige lus: een deterministische limiet/stopconditie wordt vooraf vastgelegd. Bij overschrijding -> `BLOCKED_REVIEW_LOOP` en menselijke inspectie.

### Fase F — acceptatiegate

Tier-A acceptatie alleen wanneer:
1. alle relevante deterministische tests slagen;
2. point-in-time/provenancevoorwaarden slagen;
3. Astra exact de huidige candidate-hash met `PASS` heeft beoordeeld;
4. geen open kritieke bezwaren bestaan;
5. guardrails intact zijn;
6. geen stille modeldegradatie heeft plaatsgevonden.

## 7. Minimale deterministische testset

Voor acceptatie minimaal testen:
- Sol kan geautoriseerde buildtaak ontvangen;
- Astra kan niet als builder-output worden uitgevoerd;
- reviewer is onafhankelijk van builderrun;
- review bindt aan exact candidate-hash;
- wijziging na review maakt eerdere PASS ongeldig;
- `CHANGES_REQUIRED` maakt precies één revisietaak;
- retry/restart veroorzaakt geen dubbele build/review;
- worker-busy behoudt durable outbox;
- ontbrekende Astra-capaciteit -> `REQUIRES_HIGH_INTELLIGENCE_REVIEW`;
- provenance mismatch -> fail closed;
- test failure -> geen review-PASS/acceptatie;
- max revisielus -> `BLOCKED_REVIEW_LOOP`;
- live trading, wallet en kosten blijven ongeautoriseerd;
- `NO_PROVEN_EDGE` kan niet door deze buildpipeline zelf worden opgewaardeerd.

## 8. Migratie

Niet in één stap omschakelen.

1. huidige enforcement-map vastleggen;
2. tests voor bestaand gedrag toevoegen;
3. nieuwe rolvelden introduceren zonder oude route te verwijderen;
4. Sol builderpad in geïsoleerde test activeren;
5. Astra reviewpad testen;
6. crash/retry/exact-once testen;
7. end-to-end dry-run zonder live/cost capabilities;
8. onafhankelijke Tier-A review;
9. pas daarna oude Astra-only-buildrestricties gecontroleerd verwijderen/vervangen.

Rollback moet de vorige gekwalificeerde configuratie kunnen herstellen zonder queue/evidence/provenance te verliezen.

## 9. Niet wijzigen als onderdeel van dit PvA

Zonder afzonderlijke Tier-A beoordeling niet wijzigen:
- wetenschappelijk criterium voor `PROVEN_EDGE`;
- settlementinterpretatie;
- fill/executionmodel;
- trading authorization;
- wallet/crypto;
- kostenregels;
- evidence-cutoffs;
- bestaande onderzoeksresultaten.

## 10. Definition of Done

De architectuur is pas klaar wanneer aantoonbaar geldt:

```
Sol builds
-> deterministic verification passes
-> Astra independently reviews exact artifact
-> CHANGES_REQUIRED loops safely back to Sol
-> PASS cannot bypass deterministic gates
-> every run is attributable and replayable
-> no silent degradation
-> no duplicate work after crash/retry
-> existing safety/scientific guardrails remain intact
```

Tot dat moment: `PLANNED/IN_PROGRESS`, nooit stilzwijgend `ACCEPTED`.
