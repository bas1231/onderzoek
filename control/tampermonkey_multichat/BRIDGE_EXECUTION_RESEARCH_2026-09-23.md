# Bridge execution research — 2026-09-23

## Doel

Vastleggen hoe de actuele ChatGPT ↔ WSL multi-chat bridge werkelijk werkt en hoe ChatGPT veilig lokale development/repair-taken kan uitvoeren zonder vrije shell-strings uit de chat.

## Bevestigde transportlaag

Canonical zichtbare commandmarker:

`[[PREDICTION_CMD:<ACTION>:<TASK_ID>]]`

De marker moet als gewone zichtbare assistanttekst in ChatGPT staan. De roundtrip is pas geslaagd wanneer `RESULT_READY` exact dezelfde `TASK_ID` teruggeeft.

Lokale keten:

- `8765`: wake/result bridge;
- `8767`: multi-chat command router;
- `8766`: command receiver.

De command receiver draait uit:

`/home/leonh/.local/share/prediction-chat-bridge/command_receiver.py`

Niet uit de Git worktree zelf.

## Authenticatie en actuele action-whitelist

De receiver leest zijn Bearer-token uit:

`~/.config/prediction-chat-bridge/token`

`GET /health` vereist `Authorization: Bearer <token>`.

De actuele receiver-whitelist bevat expliciet alleen:

- `BRIDGE_PING`
- `SIX_AI_HEALTH`

Daarom worden zelfbedachte action-namen zoals `DIRECTOR_FIX_GIT_INDEX`, `WEATHER_STATUS` of `BRIDGE_CAPABILITIES` terecht geweigerd / niet uitgevoerd.

## Belangrijke bestaande execution-route: DEV_TASK_ASYNC_V2

De receiver bevat al de async DEV-task route. Developmenttaken hoeven dus niet als nieuwe top-level receiver-action te worden toegevoegd.

De bestaande tunnel gebruikt:

`[[PREDICTION_CMD:SIX_AI_HEALTH:DEV-<UNIEKE-TASK-ID>]]`

Wanneer de task-ID met `DEV-` begint, wordt de bestaande async dev-task worker gebruikt. Het resultaat komt via dezelfde bridge terug met action `SIX_AI_HEALTH`.

De runner staat in de control-repo:

`/home/leonh/fg_assistent/dev_task_runner.py`

Task manifests worden door de runner rechtstreeks uit `origin/main` van `fg_assistent` geladen vanaf:

`dev_tasks/<TASK_ID>.json`

Daardoor kan ChatGPT een manifest op GitHub committen en vervolgens alleen de unieke task-ID via de zichtbare bridge-marker sturen. Vrije shelltekst uit ChatGPT wordt niet uitgevoerd.

## DEV task veiligheidsmodel

Schema: `DEV_TASK_V1`.

Belangrijke harde gates in `dev_task_runner.py`:

- task-ID moet voldoen aan een beperkte regex;
- project moet expliciet in `PROJECTS` staan;
- `live_trading` moet `false` zijn;
- `paid_actions` moet `false` zijn;
- `network_devices` moet `false` zijn;
- commands zijn argv-lijsten, geen shellstrings;
- `bash`, `sh`, `zsh`, `fish`, `sudo`, `ssh`, `curl`, `wget`, `rsync`, `nmap`, enz. zijn geblokkeerd;
- Python `-c` is geblokkeerd;
- Python scripts moeten binnen de projectroot liggen;
- netwerk/device-referenties worden geblokkeerd;
- Python child-processen krijgen de runtime network guard en zijn loopback-only.

Allowlisted projecten bevatten onder andere:

- `fg_assistent`
- `prediction_research_prod`
- `prediction_research_recon`
- `proof_hunter`
- `surplus_maker`
- `predictionbot_scan`

Toegestane Git-subcommands omvatten o.a. `status`, `diff`, `log`, `show`, `rev-parse`, `checkout`, `restore`, `add`, `commit`, `branch`, `switch`, `merge-base`, `ls-files`, `grep`, `clean`.

## Operationeel patroon vanaf nu

Voor lokaal onderzoek/build/repair:

1. maak via GitHub een uniek `dev_tasks/DEV-....json` manifest in `bas1231/fg-assistent`;
2. laat het manifest alleen allowlisted projectpaden/argv-commands uitvoeren;
3. stuur in ChatGPT `[[PREDICTION_CMD:SIX_AI_HEALTH:DEV-....]]`;
4. wacht op `RESULT_READY` met exact dezelfde task-ID;
5. beoordeel exitcode/output en maak zo nodig een volgende kleine task;
6. behoud de bestaande harde grenzen: geen live trading, paid actions, wallets, credential abuse of ongeautoriseerde netwerkacties.

Dit maakt de bestaande bridge bruikbaar voor gecontroleerde builds en repairs zonder een generieke remote shell aan ChatGPT bloot te stellen.

## Huidige Director-status tijdens dit onderzoek

De eerdere blokkade `git index is not empty` is handmatig opgeheven door de drie staged bestanden te unstagen. Daarna verschoof de Director-fout naar:

`unexpected tracked changes: AGENTS.md, control/tampermonkey_multichat/prediction-chat-wake.user.js`

De volgende stap is daarom eerst de twee diffs read-only via een DEV-task inspecteren; niet blind restoren of committen.

## Bewijsstatus

Bewezen op 2026-09-23:

- zichtbare `BRIDGE_PING` roundtrip: PASS;
- exacte task-ID routing: PASS;
- `SIX_AI_HEALTH` via bridge: PASS;
- receiver-path en whitelist: lokaal geïnspecteerd;
- Bearer-auth bron: lokaal geïnspecteerd;
- `dev_task_runner.py` en `DEV_TASK_V1` manifestmodel: op GitHub geïnspecteerd;
- `prediction_research_prod` staat in de DEV-runner projectallowlist.

Nog te bewijzen na deze notitie: een verse `DEV-...` capability probe die vanuit deze chat daadwerkelijk in `prediction_research_prod` draait en terugkomt via `RESULT_READY`.
