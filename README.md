# Prediction Market Research Knowledge Base

Status: **RESEARCH ONLY — NO_PROVEN_EDGE**

> **ChatGPT / nieuwe Prediction-sessie:** lees eerst [`00_CHATGPT_START_HERE.md`](00_CHATGPT_START_HERE.md). Dat bestand is de verplichte start voor lokale WSL-uitvoering, command-bus routing en de projectexecutor. Gebruik niet automatisch oudere bridge-instructies uit chatgeheugen.

Deze repository is de canonieke, agent-leesbare kennislaag voor **venue-onafhankelijk onderzoek naar prediction markets**. Kalshi is een belangrijke venue, maar niet het centrum of de grens van het project. Het doel is niet om winstgevendheid te veronderstellen, maar om bekende feiten, mechanismen, hypotheses, falsificaties, experimenten en execution-beperkingen zodanig vast te leggen dat AI-agents continu nieuwe toetsbare verbanden kunnen ontdekken zonder eerder onderzoek steeds opnieuw te doen.

De overkoepelende methodologie staat in `methodology/CONTINUOUS_PREDICTION_MARKET_RED_TEAM.md`.

## Missie

Behandel prediction markets als een continu economisch/contractueel attack surface:

`scope -> discover -> prioritize -> falsify -> execution proof -> learn -> repeat`

De belangrijkste asset is de cumulatieve kennisbank van mechanismen, venue-capabilities, succesvolle falsificaties, negatieve evidence en bewezen execution-beperkingen.

## Harde onderzoeksregel

Een interessante formule, prijsafwijking of mechanisme is geen edge. Promotie vereist minimaal:

`rules/payoff proof -> point-in-time executable data -> fees/depth/slippage -> historische execution-realistische replay -> validation -> untouched holdout -> prospectieve shadow/canary -> pas daarna eventueel micro-live`

`NO_PROVEN_EDGE` is een geldig eindresultaat.

## Repository-rol

Deze repo is de **kennisindex en canonieke researchlaag**. Grote ruwe datasets/orderbook-tapes horen buiten Git; hier bewaren we hun manifests, hashes, conclusies en provenance.

Belangrijk: deze repository stond bij bootstrap publiek. Daarom worden hier geen credentials, API keys, private accountdetails, geheime evidence-paden of andere gevoelige gegevens gekopieerd. Bronrepo's kunnen privé zijn; verwijzingen naar repo/pad/branch dienen als provenance.

## Structuur

- `meta/` — broninventaris, ingeststatus en repository-provenance.
- `methodology/` — vaste onderzoeks- en bewijsregels voor mensen en agents.
- `knowledge/kalshi/` — venue-specifieke Kalshi claims, hypotheses en resultaten.
- `knowledge/cross_venue/` — relaties/mechanismen die meerdere venues raken.
- toekomstige `knowledge/<venue>/` — venue-specifieke kennis voor andere prediction markets.
- `knowledge/dark_market_intelligence/` — uitsluitend intelligence uit publieke/academische/forensische bronnen over illegale/dark-web marktmechanismen; geen execution-lane.
- `negative_evidence/` — gefalsificeerde of verzwakte ideeën; nooit verwijderen omdat ze niet werkten.

## Statusvocabulaire

- `FACT_VERIFIED` — rechtstreeks ondersteund door primaire/documentaire of gereproduceerde evidence.
- `OBSERVED` — point-in-time waargenomen, maar geen algemene claim.
- `HYPOTHESIS_UNTESTED` — toetsbare hypothese zonder voldoende test.
- `TESTED_NEGATIVE` — hypothese/route is door de vastgelegde test niet ondersteund of formeel afgesloten.
- `STRUCTURAL_CANDIDATE` — geldig mechanisme, maar economische/execution-edge nog onbewezen.
- `RESEARCH_POSITIVE` — een tussengate is gehaald; dit betekent nadrukkelijk niet winstgevend.
- `EXECUTION_BLOCKED` — mechanisme kan conceptueel bestaan maar is voor de onderzochte route niet veilig/rechtmatig/economisch uitvoerbaar.
- `NO_PROVEN_EDGE` — huidige economische standaardstatus.

## Agentregel

Agents mogen hypotheses combineren en nieuwe candidates voorstellen, maar moeten altijd:

1. bestaande negatieve evidence controleren;
2. bron + datum + point-in-time beschikbaarheid bewaren;
3. onderscheid maken tussen payout-identiteit, signal edge, market edge en execution edge;
4. tegenstrijdige evidence bewaren in plaats van overschrijven;
5. nooit later beschikbare informatie terugprojecteren;
6. nooit `PROVEN_EDGE` afleiden uit alleen backtest, UI-prijs, midpoint, last trade of theoretische payoff;
7. nieuwe post-hoc ideeën opnieuw op untouched data testen;
8. adaptive search / multiple-hypothesis risk expliciet registreren;
9. nieuwe strategy-builds alleen starten na een pre-build warrant volgens de continuous-red-team methodologie.

## Wereldwijde researchscope

Discovery is venue-onafhankelijk en wereldwijd. Geografische beschikbaarheid is geen reden om een venue, product of mechanisme niet te bestuderen.

Dark-web/illicit markets mogen als **intelligencebron** worden onderzocht via publieke academische datasets, forensische publicaties, threat-intelligence/OSINT en andere rechtmatig beschikbare bronnen. Deelname, financiering of execution op illegale markten is geen onderdeel van dit project.

## Scopegrens

**Legaal grijs, vreemd, onbedoeld of economisch ongunstig voor een venue is in scope. Illegale uitvoering is een harde stop.**

Onderzoek naar legale contract-, settlement-, collateral-, fee-, information-, behavioral-, oracle- en microstructurele inefficiënties is in scope. Marktmanipulatie, fraude, misleiding, sabotage, credentialmisbruik, ongeautoriseerde toegang en operationeel misbruik van softwarekwetsbaarheden zijn niet in scope. Publieke security-/incidentinformatie mag wel als defensieve, intelligence- of falsificatiecontext worden vastgelegd zonder exploit-instructies.

## Actuele lokale ChatGPT ↔ WSL uitvoering

De primaire uitvoeringsmethode is nu de private GitHub **command bus** met de capability-scoped **project executor**.

Architectuur:

`ChatGPT -> private GitHub command bus -> read-only WSL poller/router -> project executor -> WSL -> wake/result bridge -> dezelfde ChatGPT-sessie`

Voor iedere nieuwe Prediction-sessie die lokale uitvoering nodig kan hebben:

1. lees eerst `00_CHATGPT_START_HERE.md`;
2. lees daarna `control/bridge_commands/CURRENT_STATE.md` en `control/bridge_commands/SESSION_ROUTING.md`;
3. stel een session-specific `route_task_id` vast uit een taak die aantoonbaar naar **diezelfde chat** terugkwam;
4. gebruik voor normale lokale opdrachten een verse immutable task onder `control/bridge_commands/inbox/<TASK_ID>.json`;
5. gebruik voor code/build/test/beheer de projectexecutor via `control/project_tasks/<TASK_ID>.json` plus het matching `bas1231/fg-assistent/dev_tasks/<TASK_ID>.json` manifest;
6. claim alleen succes wanneer hetzelfde task-ID terugkomt met de verwachte status en assertions.

De zichtbare `[[PREDICTION_CMD:...]]` DOM/Tampermonkey-route is alleen fallback/route-bootstrap voor een nieuwe chat zonder bewezen sessieroute; hij is niet meer de primaire commandotransport.

Harde grenzen blijven bestaan: geen sudo/root, geen autonome WSL GitHub-push, geen credential writes, geen live trades/orders, geen wallet/crypto/fund movement en geen betaalde actie zonder expliciete goedkeuring voor die specifieke actie.

Bewezen actuele same-chat command-bus baseline op 2026-09-29: `BRIDGE-COMMAND-BUS-CURRENT-ROUTE-E008` → `status=PASS exit=0`.

Volledige canonical instructies:

- `00_CHATGPT_START_HERE.md`
- `control/NEW_SESSION_LOCAL_EXECUTION.md`
- `control/bridge_commands/CURRENT_STATE.md`
- `control/bridge_commands/SESSION_ROUTING.md`
- `control/PROJECT_EXECUTOR.md`
- `control/bridge_commands/OPERATIONS.md`
- `control/tampermonkey_multichat/PROTOCOL.md`
- `control/tampermonkey_multichat/CHATGPT_PROJECT_INSTRUCTIONS.md`
- `PREDICTION_GPT_PROJECT_INSTRUCTIONS.md` — paste-ready blok voor ChatGPT Project Instructions.
