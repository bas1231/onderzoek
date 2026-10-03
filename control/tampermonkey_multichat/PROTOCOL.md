# Prediction Chat ↔ WSL Bridge Protocol

Status: canonical, provisional Tier-A infrastructure
Protocolversie: 0.7
Vastgelegd: 2026-09-29
Qualification: `REQUIRES_HIGH_INTELLIGENCE_REVIEW`

## Doel

Dit document beschrijft de actuele Prediction-commandoroute tussen ChatGPT en lokale WSL.

De primaire heenweg gebruikt geen ChatGPT-DOM-detectie. Nieuwe sessies gebruiken voor normale opdrachten de private GitHub command bus.

## Primaire architectuur

Command path:

`ChatGPT assistant -> private GitHub repo -> read-only local poller -> localhost:8767 command router -> localhost:8766 command receiver -> WSL`

Result path:

`WSL -> localhost:8765 wake bridge -> ChatGPT`

Na installatie van de inflight-patch gebruikt de result queue:

`outbox -> inflight -> sent`

Een normaal resultevent wordt atomair van `outbox` naar `inflight` verplaatst voordat `/next` het aan de browser teruggeeft. Ambigue levering van normale command-resultaten wordt niet stil herhaald of als sent beschouwd.

## Primaire commandoprotocol: GitHub command bus

Canonical operations-document:

`control/bridge_commands/OPERATIONS.md`

Schema:

`control/bridge_commands/COMMAND_SCHEMA_V1.json`

Een ChatGPT-sessie maakt via de GitHub connector precies één nieuw bestand aan:

`control/bridge_commands/inbox/<TASK_ID>.json`

Task-ID's zijn immutable en uniek. Wijzig of hergebruik een bestaand command-task-ID nooit. Bij een fout wordt een nieuwe task aangemaakt.

Verplichte safetyvelden:

- `live_trading: false`
- `paid_actions: false`
- `wallet_actions: false`

De lokale poller faalt gesloten wanneer één van deze velden niet exact `false` is.

De poller schrijft nooit naar GitHub en raakt de production working tree `~/prediction_research_prod` niet aan. Remote fetch gebeurt in een aparte lokale mirror.

## Routing

Een command kan `route_task_id` bevatten. Dan gebruikt de poller de bestaande lokale route van die taak.

Zonder `route_task_id` gebruikt de poller de lokaal gepinde route:

`~/.config/prediction-command-bus/route.json`

Bij meerdere actieve Prediction-sessies is expliciete per-command routing de standaard; de globale pinned route is dan niet voldoende.

### Automatische bootstrap voor een nieuwe chat

Sinds `DEV-PRED-SESSION-BOOTSTRAP-INSTALL-20260929-E010` is server-side automatische session bootstrap geïnstalleerd.

De bestaande Prediction Chat Wake userscript pollt `/next` al met een stabiele `chat_id` plus `consumer_id`. De wake server gebruikt die informatie om voor een chat zonder eerder bewezen routed result automatisch een chat-scoped route aan te maken en een klein idempotent resultevent terug te sturen:

`NIGHTSHIFT_WSL_RESULT_V1 task=SESSION-ROUTE-... status=PASS exit=0 kind=SESSION_ROUTE_BOOTSTRAP`

Na ontvangst in dezelfde chat wordt die `SESSION-ROUTE-*` task-ID de `route_task_id` voor normale GitHub command-bus taken uit die sessie.

Een zichtbare assistant `[[PREDICTION_CMD:...]]` marker is niet langer de normale bootstrapmethode. Legacy/menu PING blijft alleen diagnostische fallback.

De bootstrap voert geen projectcommand uit. Het is uitsluitend idempotente routingmetadata. Een stale/ambigue bootstrap-announcement mag na een begrensde delay opnieuw worden aangekondigd; deze uitzondering geldt niet voor normale command execution en verandert de at-most-once commandosemantiek niet.

Canonical routing-document:

`control/bridge_commands/SESSION_ROUTING.md`

## Durable command semantics

De poller voert deterministische schema-, safety-, provenance- en deduplicatiechecks uit.

Voor iedere normale command-task wordt vóór localhost-dispatch een duurzame lokale claim geschreven. Hierdoor geldt fail-closed at-most-once dispatch:

- `DISPATCHED`: localhost bevestigde 2xx + `ok:true`;
- `REJECTED`: deterministisch ongeldig of localhost expliciet geweigerd;
- `AMBIGUOUS`: request kan wel of niet zijn aangekomen; nooit automatisch retryen;
- `BLOCKED_ROUTE`: geen geldige route; geen dispatch uitgevoerd.

Wanneer hetzelfde command-task-ID later met andere bytes verschijnt: `TASK_ID_CONTENT_CONFLICT`; niet uitvoeren.

## Result queue semantics

Na inflight-installatie:

- `outbox/`: nog niet geleased;
- `inflight/`: exact eenmaal geleased; browserlevering kan bevestigd of ambigu zijn;
- `sent/`: browser-ACK bevestigd;
- `quarantine/`: bewaarde legacy/ambigue evidence; niet als sent behandelen.

Normale command-resultaten krijgen geen automatische `inflight -> outbox` retry. Replay vereist een expliciete gecontroleerde handeling. Alleen de idempotente `SESSION-ROUTE-*` bootstrap-announcement heeft een aparte begrensde re-announcementregel, omdat daarbij geen command opnieuw wordt uitgevoerd.

## Legacy zichtbare DOM-route

Het oude zichtbare protocol blijft uitsluitend diagnostische fallback:

`[[PREDICTION_CMD:<ACTION>:<TASK_ID>]]`

Regels:

- gebruik dit niet als primaire commandotransport;
- gebruik dit niet als normale new-session bootstrap;
- `ACTION` moet receiver-allowed zijn;
- `TASK_ID` moet uniek zijn;
- niet escapen en niet in een code fence zetten;
- voor bridge-diagnose is `BRIDGE_PING` toegestaan;
- PASS vereist dezelfde task-ID, action `BRIDGE_PING`, exit code `0` en `BRIDGE_PONG`.

De DOM-route is op 2026-09-29 onbetrouwbaar gebleken voor assistant -> WSL commandodetectie en mag niet opnieuw als primaire route worden aangenomen zonder nieuwe Tier-A kwalificatie.

## Services en paden

Command bus runtime:

- `~/.local/share/prediction-command-bus/command_bus_poller.py`
- `~/.local/share/prediction-command-bus/repo`
- `~/.local/state/prediction-command-bus/tasks/`
- `~/.local/state/prediction-command-bus/incidents/`
- `~/.config/prediction-command-bus/route.json`
- `prediction-command-bus.service`
- `prediction-command-bus.timer`

Bridge services:

- `127.0.0.1:8765` wake/result bridge
- `127.0.0.1:8766` command receiver
- `127.0.0.1:8767` command router

Active wake wrapper after E010:

`PredictionChatWake/0.9-session-bootstrap`

Canonical source:

`control/tampermonkey_multichat/bridge_server_session_bootstrap.py`

## Bewezen baseline 2026-09-29

Functioneel bewezen:

- `BRIDGE-BUS-E001` — eerste assistant -> GitHub -> WSL -> wake bridge -> ChatGPT baseline PASS;
- `BRIDGE-BUS-AUTO-20260929-E001` — automated command-bus PASS;
- `TM-PING-1790690332005` — session-specific route returned to intended chat PASS;
- `BRIDGE-COMMAND-BUS-CURRENT-ROUTE-E008` — GitHub command bus over explicit same-chat route PASS;
- `DEV-PRED-SESSION-BOOTSTRAP-INSTALL-20260929-E010` — automatic session-bootstrap regression tests, compile checks, runtime install, wake-service restart/is-active check and installed-runtime canary PASS.

De laatste externe acceptatie voor automatic bootstrap is een werkelijk nieuwe Prediction-chat die zonder DOM marker of handmatige ping automatisch zijn eigen `SESSION-ROUTE-*` PASS ontvangt. Zie `control/bridge_commands/CURRENT_STATE.md` voor actuele evidence.

## Nieuwe sessies

Een nieuwe Prediction-sessie leest eerst:

1. `00_CHATGPT_START_HERE.md`
2. `control/bridge_commands/CURRENT_STATE.md`
3. `control/bridge_commands/SESSION_ROUTING.md`
4. `control/NEW_SESSION_LOCAL_EXECUTION.md`
5. `control/PROJECT_EXECUTOR.md`
6. `control/bridge_commands/OPERATIONS.md`
7. dit `PROTOCOL.md`
8. `control/tampermonkey_multichat/CHATGPT_PROJECT_INSTRUCTIONS.md`

Wacht bij een volledig nieuwe chat op de automatische `SESSION-ROUTE-*` PASS en gebruik die daarna expliciet als `route_task_id`. Bij conflict met oudere bridge-documentatie of sessiegeheugen is dit protocol samen met `CURRENT_STATE.md` en `SESSION_ROUTING.md` autoritatief.


## Assistant-side delivery receipt

Current transport supports an assistant-side durable receipt in addition to browser ACK.

When a delivered result contains an exact event identifier, ChatGPT may acknowledge the transport by creating the deterministic immutable receipt described in `control/bridge_commands/OPERATIONS.md` and `control/bridge_commands/RESULT_RECEIPT_SCHEMA_V1.json`.

This receipt reuses the existing wake `/ack` path after local event/task/route verification. It therefore does not weaken `outbox -> inflight -> sent` semantics.

Important: a delivery receipt proves only that the message reached ChatGPT. It does **not** mean a continuation is logically complete. Raw `NIGHTSHIFT_WSL_RESULT_V1` still does not authorize NEXT/DONE/BLOCKED. A `PREDICTION_CONTROL_CONTINUE_V2` still requires exactly one durable outcome under the continuation protocol.
