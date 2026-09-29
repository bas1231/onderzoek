# Prediction Chat ↔ WSL Bridge Protocol

Status: canonical, provisional Tier-A infrastructure
Protocolversie: 0.6
Vastgelegd: 2026-09-29
Qualification: `REQUIRES_HIGH_INTELLIGENCE_REVIEW`

## Doel

Dit document beschrijft de actuele Prediction-commandoroute tussen ChatGPT en lokale WSL.

De primaire heenweg gebruikt niet langer ChatGPT-DOM-detectie. Nieuwe sessies moeten voor normale opdrachten de private GitHub command bus gebruiken.

## Primaire architectuur

Command path:

`ChatGPT assistant -> private GitHub repo -> read-only local poller -> localhost:8767 command router -> localhost:8766 command receiver -> WSL`

Result path:

`WSL -> localhost:8765 wake bridge -> ChatGPT`

Na installatie van de inflight-patch gebruikt de result queue:

`outbox -> inflight -> sent`

Een event wordt atomair van `outbox` naar `inflight` verplaatst voordat `/next` het aan de browser teruggeeft. Een ambigu browserresultaat blokkeert daardoor nooit nieuwere resultaten en wordt niet automatisch opnieuw aangeboden.

## Primaire commandoprotocol: GitHub command bus

Canonical operations-document:

`control/bridge_commands/OPERATIONS.md`

Schema:

`control/bridge_commands/COMMAND_SCHEMA_V1.json`

Een ChatGPT-sessie maakt via de GitHub connector precies één nieuw bestand aan:

`control/bridge_commands/inbox/<TASK_ID>.json`

Task-ID's zijn immutable en uniek. Wijzig of hergebruik een bestaand task-ID nooit. Bij een fout wordt een nieuwe task aangemaakt.

Verplichte safetyvelden:

- `live_trading: false`
- `paid_actions: false`
- `wallet_actions: false`

De lokale poller faalt gesloten wanneer één van deze velden niet exact `false` is.

De poller schrijft nooit naar GitHub en raakt de working tree `~/prediction_research_prod` niet aan. Remote fetch gebeurt in een aparte lokale mirror.

## Routing

Een command kan optioneel `route_task_id` bevatten. Dan gebruikt de poller de bestaande lokale route van die taak.

Zonder `route_task_id` gebruikt de poller de lokaal gepinde route:

`~/.config/prediction-command-bus/route.json`

De eerste bewezen control-route is `BRIDGE-BUS-E001` van 2026-09-29.

Als een nieuwe ChatGPT-chat nog geen lokale route heeft, mag uitsluitend voor route-bootstrap de legacy Tampermonkey-route of menu-PING worden gebruikt. Daarna kan die route als nieuwe control-route worden gepind.

## Durable command semantics

De poller voert deterministische schema-, safety-, provenance- en deduplicatiechecks uit.

Voor iedere task wordt vóór localhost-dispatch een duurzame lokale claim geschreven. Hierdoor geldt fail-closed at-most-once dispatch:

- `DISPATCHED`: localhost bevestigde 2xx + `ok:true`;
- `REJECTED`: deterministisch ongeldig of localhost expliciet geweigerd;
- `AMBIGUOUS`: request kan wel of niet zijn aangekomen; nooit automatisch retryen;
- `BLOCKED_ROUTE`: geen geldige route; geen dispatch uitgevoerd.

Wanneer dezelfde task-ID later met andere bytes verschijnt: `TASK_ID_CONTENT_CONFLICT`; niet uitvoeren.

## Result queue semantics

Na inflight-installatie:

- `outbox/`: nog niet geleased;
- `inflight/`: exact eenmaal geleased; levering kan bevestigd of ambigu zijn;
- `sent/`: browser-ACK bevestigd;
- `quarantine/`: bewaarde legacy/ambigue evidence; niet als sent behandelen.

Er is geen automatische `inflight -> outbox` retry. Replay vereist een expliciete, gecontroleerde handeling.

## Legacy zichtbare DOM-route

Het oude zichtbare protocol blijft alleen diagnostische fallback:

`[[PREDICTION_CMD:<ACTION>:<TASK_ID>]]`

Regels:

- gebruik dit niet als primaire commandotransport;
- `ACTION` moet receiver-allowed zijn;
- `TASK_ID` moet uniek zijn;
- niet escapen en niet in een code fence zetten;
- voor bridge-diagnose is `BRIDGE_PING` toegestaan;
- PASS vereist dezelfde task-ID, action `BRIDGE_PING`, exit code `0` en `BRIDGE_PONG`.

De oude DOM-route is in 2026-09-29 onbetrouwbaar gebleken voor assistant -> WSL commandodetectie en mag niet opnieuw als primaire route worden aangenomen zonder nieuwe Tier-A kwalificatie.

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

## Installatie

Canonical installer:

`control/bridge_commands/install_command_bus.py`

Deterministische self-tests:

`control/bridge_commands/selftest.py`

De installer:

1. controleert bestaande 8765/8766/8767 services;
2. gebruikt een aparte read-only Git mirror;
3. pint een bewezen chatroute;
4. seeddet eerder bewezen `BRIDGE-BUS-E001` zodat die niet opnieuw wordt uitgevoerd;
5. stopt tijdelijk de wake service;
6. bewaart bestaande outbox-events in quarantine met hashes/manifest;
7. patcht de actieve wake-server narrow/in-place naar fail-closed inflight;
8. start en health-checkt de wake service;
9. installeert de 30-seconden command-bus timer;
10. houdt qualification op `REQUIRES_HIGH_INTELLIGENCE_REVIEW` totdat onafhankelijke Tier-A review gereed is.

## Bewezen baseline 2026-09-29

Task: `BRIDGE-BUS-E001`

Bewezen:

- assistant schreef command naar private GitHub repo;
- WSL fetchte het command read-only;
- router antwoordde HTTP 200, `exit_code:0`, `routed:true`;
- matching result-event werd lokaal aangemaakt;
- na verwijderen van oudere queue blockers ontving ChatGPT:
  `NIGHTSHIFT_WSL_RESULT_V1 task=BRIDGE-BUS-E001 status=PASS exit=0`.

Conclusie: functionele end-to-end baseline PASS. Finale Tier-A kwalificatie is nog niet verleend.

## Nieuwe sessies

Een nieuwe Prediction-sessie moet eerst lezen:

1. `control/bridge_commands/OPERATIONS.md`
2. dit `PROTOCOL.md`
3. `control/tampermonkey_multichat/CHATGPT_PROJECT_INSTRUCTIONS.md`

Bij conflict met oudere bridge-documentatie of sessiegeheugen is dit protocol autoritatief.
