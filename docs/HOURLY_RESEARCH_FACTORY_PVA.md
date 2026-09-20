# PVA — Hourly Research Factory V1

Datum: 2026-09-20
Status: **BUILD IN PROGRESS — RESEARCH ONLY — NO_PROVEN_EDGE**

## 1. Doel

Bouw één doorlopende prediction-market research-factory waarin:

- Git de canonieke kennisbank en audit trail is;
- ChatGPT de Research Director is;
- ieder actief uur nieuwe gratis/publieke informatie wordt gezocht;
- nieuwe evidence gericht tegen bestaande hypotheses, negative evidence, candidates en eerdere runs wordt gehouden;
- evidence naar specialistische agents wordt gerouteerd;
- zwakke ideeën vóór engineering worden gedood;
- alleen survivors naar zwaardere replay/validation/holdout/shadow gaan;
- alle duurzame conclusies, inclusief negatives en onzekerheid, terug naar Git gaan;
- economische standaardstatus `NO_PROVEN_EDGE` blijft totdat alle vereiste gates expliciet zijn gehaald.

Dit vervangt de oude gedachte dat losse legacy-systemen zoals Radar V4 of Proof Trader de hourly agentlaag vormen.

## 2. Canonieke architectuur

```text
ACTIVE HOUR
   |
   v
CADENCE GATE (4h work / 1h cooldown)
   |
   v
SOURCE SWEEP / SCOUT
   |
   +--> archive manifest + hashes
   +--> change detection
   +--> text extraction
   +--> source quality
   |
   v
ROLE ROUTER
   |
   +--> weather_twc
   +--> microstructure
   +--> behavioral
   +--> informed_flow
   +--> algebra
   +--> settlement
   +--> scout/general discovery
   |
   v
TARGETED GIT MEMORY
   |
   +--> canonical methodology
   +--> negative evidence
   +--> active candidates
   +--> recent hourly reports
   +--> relevant prior knowledge/experiments
   |
   v
PRE-BUILD KILLER
   |
   v
CHIEF FALSIFIER
   |
   +--> semantic/source attack
   +--> statistical/data attack
   +--> execution/economic attack
   |
   v
INDEPENDENT REPRODUCER (alleen waar gerechtvaardigd)
   |
   v
RESEARCH DIRECTOR
   |
   +--> KILL / PARK / KEEP RESEARCHING / PROMOTION CANDIDATE
   +--> write durable knowledge to Git
   +--> publish hourly report
```

## 3. Rollen

De machineleesbare bron van waarheid is `agents/registry.json`.

### Scout
Brede discovery van publieke evidence, venues, producten, rule changes, papers, code, datasets, incidenten en anomalieën.

### Weather/TWC
Onderzoek hourly weather, TWC settlement en nowcasting. Signal edge en market edge blijven aparte claims.

### Microstructure
Onderzoek spread, depth, queue, maker/taker, fills, cancellations, latency, slippage, partial fills en adverse selection.

### Behavioral
Onderzoek onder meer favorite-longshot, framing/YES bias, anchoring, recency, FOMO, herding en probability calibration.

### Informed Flow
Onderzoek alleen publiek observeerbare information-flow signatures zoals order-flow imbalance, unusual flow en cancellations. Geen niet-openbare informatie of persoonsidentificatie.

### Algebra
Zoek payout identities, complements, ranges, thresholds, exact-value relaties, MVE/combo, mutually-exclusive/netted en cross-series/cross-venue constructies.

### Settlement
Controleer contracttekst, source, revisions, rounding, deadlines, disputes, oracle/finality en source/version drift.

### Pre-Build Killer
Kill goedkope slechte ideeën vóór engineering. Vereist novelty, semantics, economic headroom, cheap empirical evidence en execution spotcheck.

### Chief Falsifier
Valt iedere materiële kandidaat vanuit onafhankelijke failure modes aan.

### Independent Reproducer
Reproduceert high-value evidence met zo min mogelijk afhankelijkheid van de oorspronkelijke ontdekker.

### Research Director
Orkestreert, dedupliceert, bewaakt gates, schrijft status/rapportage en mag geen safety-, capital- of validation-gates omzeilen.

## 4. Git als geheugen

Git wordt niet ieder uur volledig opnieuw gelezen. De Director krijgt een begrensde, relevante memory-context.

Altijd opnemen:

- `AGENTS.md`;
- `README.md`;
- `PROJECT_IN_EEN_OOGOPSLAG.md`;
- continuous red-team methodology;
- research protocol;
- execution-first methodology;
- negative evidence ledger;
- task queue;
- agent registry;
- Director manifest.

Dynamisch opnemen:

- actieve candidates;
- laatste hourly reports;
- eerdere knowledge/experiment/negative records die matchen op de termen uit nieuwe evidence;
- relevante contradicties en failures.

Grote raw tapes blijven buiten Git. Git bewaart manifests, hashes, provenance, hypotheses, negatives, experimentresultaten en beslissingen.

## 5. Hourly discovery

Een actief uur is een researchrun, niet alleen een statusrapport.

Minimale handelingen:

1. gratis/publieke bronnen ophalen;
2. nieuwe versus reeds bekende inhoud bepalen;
3. bronkwaliteit beoordelen;
4. evidence naar rollen routeren;
5. relevante Git-memory ophalen;
6. duplicates/prior negatives detecteren;
7. waar gerechtvaardigd hypothese formuleren;
8. cheap kill-gates uitvoeren;
9. drie-hoekenfalsificatie toepassen op materiële kandidaten;
10. alleen duurzame nieuwe kennis terugschrijven;
11. hourly report publiceren, ook met `NO_PROVEN_EDGE` wanneer dat de juiste conclusie is.

## 6. 4 uur actief / 1 uur cooldown

Harde cadence:

- eerste actieve research/build-taak start een work block;
- work block duurt maximaal 4 uur;
- daarna volgt 1 volledig uur cooldown voor ChatGPT/Director/bridge-research;
- tijdens cooldown start `hourly_cycle.py` geen source sweep, packets of ChatGPT wake;
- na cooldown start de eerstvolgende actieve taak een nieuw 4-uursblok;
- passieve lokale recorders zonder OpenAI/ChatGPT mogen tijdens cooldown blijven lopen;
- cadence state staat lokaal in `~/.local/state/prediction-research/work_cadence.json`;
- corrupte cadence state faalt gesloten.

Voorbeeld:

```text
10:30 eerste taak
10:30–14:30 WORK
14:30–15:30 COOLDOWN
15:30 volgende taak -> nieuw WORK block
```

## 7. Safety en kosten

Ongewijzigde harde grenzen:

- research only;
- geen live trading;
- geen orders;
- geen wallet/fund movement;
- geen betaalde API, dataset, cloud of andere kosten zonder voorafgaande expliciete toestemming;
- alleen `free_public` bronnen in de automatische source sweep;
- geen post-close leakage;
- geen post-hoc profit optimization;
- geen operationeel misbruik van securitykwetsbaarheden;
- `ILLEGAL = HARD STOP`.

## 8. Permanente parallelle onderzoeksqueue en no-starvation

De Research Factory behandelt serieuze survivors als **stateful onderzoeksprojecten**. Een kandidaat mag nooit verdwijnen of worden afgewezen uitsluitend omdat de Research Director op dat moment onvoldoende tijd heeft.

Harde regels:

- iedere plausibele kandidaat die de goedkope kill-gates overleeft krijgt een persistent candidate record en blijft in de queue totdat er een inhoudelijke eindstatus is;
- gebrek aan Director-capaciteit is **geen** geldige reden voor `KILL`;
- meerdere experimenten mogen parallel lopen wanneer zij elkaar niet contamineren en voldoende lokale capaciteit beschikbaar is;
- lange gratis lokale berekeningen, recorders en reeds gestarte experimenten mogen zelfstandig doorlopen zonder actieve ChatGPT-tijd, ook tijdens Director-cooldown, zolang zij geen betaalde actie, live trading, walletactie of OpenAI/ChatGPT-verkeer veroorzaken;
- de Director besteedt actieve tijd primair aan beslissingen, interpretatie, ontwerp van falsificatietests en analyse van gereedgekomen resultaten; wachten op rekentijd blokkeert ander onderzoek niet;
- nieuwe kandidaten mogen oudere survivors niet onbeperkt verdringen: iedere survivor krijgt uiteindelijk opnieuw onderzoekstijd (**no-starvation**);
- iedere extra onderzoeksronde moet een concrete onbeantwoorde vraag hebben die de status of een gate kan veranderen; als verdere arbeid geen beslissende informatiewaarde meer heeft, wordt de kandidaat inhoudelijk `PARK`, niet stil vergeten;
- discovery-evidence, development, validation, holdout en prospective evidence blijven strikt gescheiden; parallelisme mag de onderzoeksprotocollen niet vervuilen.

### Queue-statussen

Minimaal ondersteunde operationele toestanden:

- `QUEUED` — geregistreerd en wacht op eerste/volgende onderzoekstaak;
- `NEEDS_DIRECTOR` — menselijke/Director-redenering of experimentontwerp nodig;
- `EXPERIMENT_REQUIRED` — concrete beslissende test is gespecificeerd maar nog niet gestart;
- `RUNNING` — lokaal experiment/recorder/replay loopt;
- `WAITING_FOR_DATA` — vooraf gespecificeerde evidence of prospectieve observaties worden verzameld;
- `WAITING_FOR_RESULT` — computationele taak loopt; geen Director-tijd nodig;
- `RESULT_READY` — resultaat staat klaar voor Director-beoordeling;
- `NEEDS_REVISION` — test/tooling bleek onvoldoende; wijziging moet expliciet worden gemotiveerd zonder post-hoc winstoptimalisatie;
- `PARKED` — inhoudelijk onvoldoende informatiewaarde of momenteel niet testbaar, met expliciete hervattingsvoorwaarde;
- `CLOSED_NEGATIVE` — overtuigend gefalsificeerd;
- `PROMOTION_CANDIDATE` — voldoende bewijs voor de volgende formele researchgate, niet gelijk aan bewezen edge.

Iedere niet-terminale kandidaat bewaart minimaal: stable candidate ID, hypothese/mechanisme, huidige researchfase, queue-status, reeds uitgevoerde tests, relevante negative evidence, open vraag, **next decisive test**, benodigde data, actieve experiment-ID's, timestamps en hervattings-/stopvoorwaarde.

### Prioritering

Prioriteit bepaalt **wanneer**, niet **of**, een survivor wordt onderzocht. De Director mag prioriteren op informatiewaarde, economische betekenis, tijdgevoeligheid, kosten/duur van de volgende falsificatietest en afhankelijkheden. Periodiek wordt expliciet gecontroleerd op oude kandidaten die te lang geen inhoudelijke voortgang kregen. Een kandidaat blijft alleen gesloten na een inhoudelijke terminale beslissing; queue-druk is nooit terminal evidence.

### Parallelle experimenten

Een kandidaat kan meerdere onafhankelijke experimenten hebben en meerdere kandidaten kunnen tegelijk `RUNNING` of `WAITING_*` zijn. De Director hoeft niet te wachten op experiment A voordat kandidaat B wordt onderzocht. Gereedgekomen experimenten gaan naar `RESULT_READY` en worden in een volgende actieve Director-run beoordeeld vanaf het opgeslagen checkpoint.


## 9. Promotion path

```text
DISCOVERED
-> MECHANISM_DEFINED
-> DATA_READY
-> DEVELOPMENT
-> VALIDATION
-> HOLDOUT
-> INDEPENDENT_REPRODUCTION
-> EXECUTION_REALITY
-> SHADOW
-> MICRO_LIVE_ELIGIBLE
```

Iedere stap kan eindigen in `TESTED_NEGATIVE`, `EXECUTION_BLOCKED`, `INSUFFICIENT_DATA` of `NO_PROVEN_EDGE`.

Geen micro-live zonder afzonderlijke expliciete toestemming voor de specifieke geld/kostenactie.

## 10. Hourly report contract

Het rapport bevat minimaal:

1. run metadata + cadence;
2. source coverage en source failures;
3. nieuwe evidence;
4. candidate hypotheses;
5. relevante bestaande Git-memory/negative evidence;
6. falsification-resultaten;
7. reproduction-status waar van toepassing;
8. coverage gaps/incidents;
9. Director-besluit;
10. `next_hour`.

Rapporteer herhaalde evidence niet opnieuw als nieuwe vondst.

## 11. Scheduler tijdens defecte Chrome-extension

Zolang de lokale Chrome/bridge-control tijdelijk niet werkt:

- ChatGPT Automations mag als tijdelijke wake/scheduler dienen;
- de automation voert de Research Director-logica uit tegen `bas1231/onderzoek`;
- geen legacy Radar/Proof-Trader jobs;
- geen lokale servicewijzigingen claimen zolang de lokale bridge niet bereikbaar is;
- Git blijft source of truth.

Zodra de bridge hersteld is:

1. branch lokaal ophalen;
2. tests uitvoeren;
3. `hourly_cycle.py` via de bestaande lokale zero-cost scheduler/timer activeren;
4. cadence state verifiëren;
5. één canary-run uitvoeren;
6. bevestigen dat cooldown-run werkelijk `COOLDOWN_SKIP` geeft;
7. tijdelijke ChatGPT scheduler verwijderen als de lokale route dezelfde functie betrouwbaar overneemt.

## 12. Acceptatiecriteria V1

### A. Cadence
- eerste taak start 4h block;
- `T+3:59:59` toegestaan;
- exact `T+4h` geblokkeerd;
- volledige volgende 1h geblokkeerd;
- exact na cooldown nieuwe block toegestaan;
- corrupte state fail-closed.

### B. Discovery
- source registry bevat uitsluitend gratis publieke sources;
- source sweep archiveert retrieval metadata + hash;
- change detection voorkomt simpele duplicate discovery;
- source quality markeert onbruikbare evidence.

### C. Memory
- canonical refs altijd aanwezig;
- negative evidence altijd aanwezig;
- actieve candidates zichtbaar;
- recente reports zichtbaar;
- dynamische matches op nieuwe routed evidence;
- raw tapes niet in Git-memory gekopieerd.

### D. Agent routing
- routed evidence per specialist zichtbaar;
- geen specialist verzint ontbrekende evidence;
- Pre-Build Killer en Chief Falsifier blijven verplicht voor promotie;
- Independent Reproducer alleen na serieuze survivor.

### E. Output
- run manifest;
- agent packets;
- routing file;
- memory-context file;
- hourly report;
- durable finding/negative indien materieel;
- default decision `NO_PROVEN_EDGE`;
- iedere niet-terminale survivor is terugvindbaar in de persistente queue;
- `RUNNING`/`WAITING_*` kandidaten worden niet als vergeten of afgerond behandeld;
- no-starvation-audit detecteert survivors zonder tijdige inhoudelijke voortgang;
- capaciteitstekort kan nooit zelfstandig een kandidaat naar `KILL`/`CLOSED_NEGATIVE` brengen.

## 13. Richting na V1

### Milestone 1 — betrouwbare hourly factory
Cadence, discovery, memory, routing en rapportage foutvrij en reproduceerbaar.

### Milestone 2 — Candidate Registry + Pre-Build Killer volledig operationeel
Nieuwe hypotheses krijgen stabiele IDs, prior-art lookup, headroom en kill-resultaat.

### Milestone 3 — mechanism/venue graph
Nieuwe venues automatisch matchen tegen bekende mechanism prerequisites.

### Milestone 4 — Execution Lab
Alleen survivors krijgen microstructure-grade replay met L2, fees, slippage, queue/fill en partial-fill modelling.

### Milestone 5 — onafhankelijke confirmation
Untouched holdout, reproduction en prospective shadow.

### Milestone 6 — micro-live eligibility
Alleen bij bewezen signal + market + execution edge en alleen na expliciete menselijke toestemming voor echte geldactie.

## 14. Succesdefinitie

Het systeem is succesvol wanneer het:

- continu nieuwe informatie kan vinden;
- niet steeds dezelfde dode ideeën herontdekt;
- slechte ideeën goedkoop doodt;
- bewijs en negatives reproduceerbaar bewaart;
- execution-fantasieën vroeg blokkeert;
- en uiteindelijk óf een robuuste edge valideert óf overtuigend `NO_PROVEN_EDGE` vaststelt.

Het aantal gevonden ideeën is geen succesmetric. Researchkwaliteit, falsificatie-efficiëntie en execution-realistische evidence zijn dat wel.
