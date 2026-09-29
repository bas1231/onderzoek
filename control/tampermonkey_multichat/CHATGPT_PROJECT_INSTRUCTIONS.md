# ChatGPT Project Instructions — Prediction bridge

Gebruik voor Prediction bridge-opdrachten het actuele protocol uit:

1. `control/bridge_commands/OPERATIONS.md`
2. `control/tampermonkey_multichat/PROTOCOL.md`
3. `control/bridge_commands/HARDENED_V8_INTEGRATION.md` wanneer de lokale wake-runtime `PredictionChatWake/0.8-hardened` gebruikt.

## Primaire route

Gebruik voor normale ChatGPT -> WSL opdrachten de private GitHub command bus. Maak via de GitHub connector precies één nieuw immutable commandbestand:

`control/bridge_commands/inbox/<TASK_ID>.json`

Volg `control/bridge_commands/COMMAND_SCHEMA_V1.json`.

Belangrijk:

- task-ID altijd uniek;
- bestaand taskbestand nooit wijzigen of hergebruiken;
- `live_trading`, `paid_actions` en `wallet_actions` moeten exact `false` zijn;
- gebruik een passende `intelligence_tier`;
- registreer werkelijk gebruikt model en reasoningniveau; als het runtime-niveau niet zichtbaar is, gebruik `UNAVAILABLE_TO_RUNTIME` en claim geen hoger niveau;
- WSL pollt GitHub read-only en mag niet automatisch pushen;
- een `AMBIGUOUS` dispatch wordt nooit automatisch opnieuw verstuurd;
- een andere payload onder hetzelfde task-ID is een conflict en mag niet worden uitgevoerd.

Zonder `route_task_id` gaat het resultaat naar de lokaal gepinde control-route. Gebruik `route_task_id` wanneer een specifieke bestaande chatroute nodig is.

## Lokale bootstrap — terminalveilig

Gebruik voor installatie/herstel uitsluitend:

`control/bridge_commands/bootstrap_local_terminal_safe.sh`

Gebruik NIET meer `git show ... | bash` en gebruik het oude `bootstrap_local.sh` niet als primaire installatie-instructie. Op 2026-09-29 sloot een mislukte pipe-bootstrap de gebruikersterminal; bovendien zat in de voorlopige installer een lowercase-Python-booleanfout die pas runtime faalde. De terminal-safe bootstrap gebruikt geen `set -e`, geen top-level `exit`, bewaakt de installerbron vóór uitvoering en rapporteert altijd `BOOTSTRAP_RC=<code>`.

Bij interactieve uitvoering: zet eerst `set +e`, schrijf de bootstrap naar een lokaal bestand en source dat bestand. Zo blijft de huidige shell open, ook als installatie of rollback faalt.

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

Voor een echte command-bus-test:

- maak een nieuw GitHub commandbestand met action `BRIDGE_PING`;
- wacht op hetzelfde task-ID in het terugkomende resultaat;
- PASS vereist action `BRIDGE_PING`, exit code `0` en `BRIDGE_PONG`.

Bewezen baseline: `BRIDGE-BUS-E001` op 2026-09-29 voltooide assistant -> private GitHub -> WSL -> result bridge -> ChatGPT met PASS.

## Qualification

Deze command-bus/inflight-architectuur is Tier A. Functionele baseline is bewezen, maar finale acceptatie blijft `REQUIRES_HIGH_INTELLIGENCE_REVIEW` totdat relevante deterministische tests, provenancevoorwaarden en een onafhankelijke Tier-A review groen zijn.

Bij conflict met oud sessiegeheugen of oudere bridge-documentatie is `PROTOCOL.md` autoritatief; voor lokale bootstrapveiligheid en hardened-v8-integratie gelden de aanvullingen hierboven.
