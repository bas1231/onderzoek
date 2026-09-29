# ChatGPT Project Instructions — Prediction bridge

Gebruik voor Prediction lokale uitvoering en bridge-opdrachten de actuele documentatie uit:

1. `control/bridge_commands/CURRENT_STATE.md`
2. `control/NEW_SESSION_LOCAL_EXECUTION.md`
3. `control/bridge_commands/OPERATIONS.md`
4. `control/PROJECT_EXECUTOR.md`
5. `control/tampermonkey_multichat/PROTOCOL.md`
6. `control/bridge_commands/HARDENED_V8_INTEGRATION.md` wanneer de lokale wake-runtime `PredictionChatWake/0.8-hardened` gebruikt.

Bij conflict met oud sessiegeheugen of oudere bridge-documentatie zijn deze canonical Git-bestanden leidend.

## Primaire route

Gebruik voor normale ChatGPT -> WSL opdrachten de private GitHub command bus. Maak via de GitHub connector precies één nieuw immutable commandbestand:

`control/bridge_commands/inbox/<TASK_ID>.json`

Volg `control/bridge_commands/COMMAND_SCHEMA_V1.json`.

Belangrijk:

- task-ID altijd uniek;
- bestaand taskbestand nooit wijzigen of hergebruiken;
- `live_trading`, `paid_actions` en `wallet_actions` moeten exact `false` zijn tenzij een afzonderlijk purpose-built pad én vereiste expliciete goedkeuring bestaan;
- gebruik een passende `intelligence_tier`;
- registreer werkelijk gebruikt model en reasoningniveau; als het runtime-niveau niet zichtbaar is, gebruik `UNAVAILABLE_TO_RUNTIME` en claim geen hoger niveau;
- WSL pollt GitHub read-only en mag niet automatisch pushen;
- een `AMBIGUOUS` dispatch wordt nooit automatisch opnieuw verstuurd;
- een andere payload onder hetzelfde task-ID is een conflict en mag niet worden uitgevoerd.

Zonder `route_task_id` gaat het resultaat naar de lokaal gepinde control-route. Gebruik `route_task_id` alleen wanneer een specifieke bestaande chatroute nodig is.

## Projectcode uitvoeren en beheren

Gebruik geen onbeperkte shell-backdoor. Voor code-uitvoering, tests, lokale Git-mutaties of Prediction user-servicebeheer geldt de capability-scoped executor uit `control/PROJECT_EXECUTOR.md` en de stap-voor-stap handleiding uit `control/NEW_SESSION_LOCAL_EXECUTION.md`.

Canonical task-spec:

`control/project_tasks/<TASK_ID>.json`

Schema:

`control/project_tasks/PROJECT_TASK_SCHEMA_V1.json`

Harde safetyflags blijven altijd `false`: `live_trading`, `paid_actions`, `wallet_actions`, `remote_git_write` en `credential_write`.

De executor is operationeel voor normale Prediction-projectwerkzaamheden binnen expliciet gedeclareerde capabilities. Bewezen functionaliteit omvat geïsoleerde worktree-writes, repository-owned Python uitvoering, tests, lokale Git add/commit/status/diff/log-operaties, allowlisted Prediction-runtime-installaties, `prediction-*` user-servicebeheer/status en Prediction journal reads.

`s​​udo`, root, credentialpaden, willekeurige externe netwerktoegang vanuit projectcode, `git push` en remote-refmutatie blijven geblokkeerd. WSL zelf blijft GitHub read-only; remote repository writes lopen via de expliciete ChatGPT GitHub-connector.

Transport loopt via de bestaande asynchrone `DEV-` tunnel met de huidige compatibility action `SIX_AI_HEALTH`; maak daarvoor een matching immutable manifest in `bas1231/fg-assistent/dev_tasks/<TASK_ID>.json` dat `project_task_executor.py` plus de guard synchroniseert en `project_task_executor.py <TASK_ID>` uitvoert. Gebruik altijd exact hetzelfde task-ID in project spec, DEV manifest en command-bus dispatch.

Een succesvolle dispatch is nog geen succesvolle code-uitvoering. Claim pas succes wanneer hetzelfde task-ID terugkomt met `status=PASS exit=0` en de bedoelde code/asserties daadwerkelijk onderdeel waren van de task.

De project-executor blijft formeel Tier A en `REQUIRES_HIGH_INTELLIGENCE_REVIEW` totdat de onafhankelijke reviewgate groen is. Die governance-status blokkeert het operationele gebruik voor normale build/test/diagnose/beheertaken niet en mag niet worden gebruikt om bestaande safety-, provenance-, trade-, wallet- of kostenregels te versoepelen.

## Lokale bootstrap — terminalveilig

Gebruik voor installatie/herstel uitsluitend:

`control/bridge_commands/bootstrap_local_terminal_safe.sh`

Gebruik NIET meer `git show ... | bash` en gebruik het oude `bootstrap_local.sh` niet als primaire installatie-instructie. Op 2026-09-29 sloot een mislukte pipe-bootstrap de gebruikersterminal; bovendien zat in de voorlopige installer een lowercase-Python-booleanfout die pas runtime faalde. De terminal-safe bootstrap gebruikt geen `set -e`, geen top-level `exit`, bewaakt de installerbron vóór uitvoering en rapporteert altijd `BOOTSTRAP_RC=<code>`.

Bij interactieve uitvoering: zet eerst `set +e`, schrijf de bootstrap naar een lokaal bestand en source dat bestand. Zo blijft de huidige shell open, ook als installatie of rollback faalt.

Normale sessies horen bootstrap of handmatige terminalstappen niet opnieuw te gebruiken wanneer de command bus/executor operationeel zijn.

## Hardened v8 runtime

Wanneer de actieve lokale `bridge_server.py` `import bridge_server_v2 as base` bevat en `PredictionChatWake/0.8-hardened` rapporteert, mag de inflight-installatie de wrapper niet vervangen of flattenen. De queue- en ACK-semantiek hoort in de sibling `bridge_server_v2.py`; de hardened wrapper moet zijn compaction, task-dedupe, heartbeat en nightshiftgedrag behouden. De installer moet beide bestanden back-uppen en op failure beide plus de outbox herstellen.

## Resultaten

De result bridge gebruikt na installatie fail-closed queue-semantiek:

`outbox -> inflight -> sent`

`inflight` betekent: exact eenmaal aan de browser aangeboden; delivery kan bevestigd of ambigu zijn. Een inflight-event wordt niet automatisch opnieuw aangeboden en blokkeert nieuwere resultaten niet.

## Legacy route — alleen diagnostisch

De zichtbare assistantmarker blijft uitsluitend fallback/diagnose:

`[[PREDICTION_CMD:<ACTION>:<TASK_ID>]]`

Gebruik hem niet meer als primaire commandotransport. De DOM-route bleek op 2026-09-29 onbetrouwbaar voor commandodetectie.

Wanneer een nieuwe chat nog geen route heeft, mag een legacy/menu `BRIDGE_PING` eenmalig worden gebruikt om een lokale route te creëren; daarna moet de GitHub command bus weer de primaire route zijn.

## Bridge-test

Voor een pure transporttest:

- maak een nieuw GitHub commandbestand met action `BRIDGE_PING`;
- wacht op hetzelfde task-ID in het terugkomende resultaat;
- PASS vereist exit code `0` en `BRIDGE_PONG`.

Voor een echte code-uitvoeringstest gebruik de project-executor flow uit `control/NEW_SESSION_LOCAL_EXECUTION.md`: schrijf een klein repository-owned Python-bestand in een geïsoleerde worktree, voer het uit, laat het een artifact schrijven/lezen/asserten en eis dezelfde task-ID met `status=PASS exit=0` terug.

Bewezen baseline omvat inmiddels command-bus E2E, project Python uitvoering en een operationele beheer-canary; zie `control/bridge_commands/CURRENT_STATE.md` voor de actuele evidence.

## Failure handling

Vraag niet direct om handmatige terminalcommando's. Diagnoseer eerst via dezelfde command bus/executor-route met een fresh immutable task-ID. Classificeer de eerste incomplete stage, patch gericht en voeg bij bugs in safety/execution een regressietest toe.

Vraag alleen om handmatige tussenkomst wanneer:

- de command bus zelf onbereikbaar is en niet autonoom gerepareerd kan worden;
- fysieke/KYC/login-interactie nodig is;
- een specifieke kosten-, trade- of walletgoedkeuring vereist is;
- een bewust niet-beschikbare capability essentieel is.

## Qualification

Deze command-bus/inflight-architectuur en projectexecutor zijn Tier A. De functionele baseline is end-to-end bewezen en operationeel bruikbaar. Finale formele acceptatie blijft `REQUIRES_HIGH_INTELLIGENCE_REVIEW` totdat de onafhankelijke Tier-A reviewgate groen is.
