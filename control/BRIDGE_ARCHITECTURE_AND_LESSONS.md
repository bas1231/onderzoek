# Browser Bridge — architectuur, werking en geleerde lessen

Status: canonical control-plane document
Datum eerste vastlegging: 2026-09-20
Scope: lokale ChatGPT ↔ Chrome-extension ↔ WSL bridge ↔ Git ↔ executor ↔ resultaat-retourketen

## Doel

Deze bridge bestaat om ChatGPT als Research Director taken naar de lokale WSL research-worker te laten sturen zonder OpenAI API, zonder live-tradingbevoegdheid en met Git als audit trail. Dit document beschrijft zowel hoe de keten is gebouwd als de concrete problemen die tijdens gebruik zijn ontdekt. Nieuwe bridgeproblemen horen hier te worden toegevoegd zodat volgende agents niet dezelfde fouten herhalen.

## Hoofdarchitectuur

De normale taakstroom is:

`zichtbare assistant-chattekst -> Chrome content script -> localhost HTTP bridge -> gevalideerde Git task -> WSL executor -> result files -> Git -> bridge outbox -> Chrome content script -> automatisch user-bericht terug naar ChatGPT`

Belangrijkste componenten:

- `control/browser_extension/content.js`
  - draait alleen in een gewapende ChatGPT-conversatie;
  - scant zichtbare assistant-berichten op expliciete bridge-taskblokken;
  - parseert JSON;
  - bewaart ontdekte geldige envelopes in een durable Chrome-local queue;
  - roept `/discover` en `/enqueue` aan;
  - pollt `/outbox` en `/ai-outbox`;
  - zet resultaten terug in de ChatGPT-composer en verstuurt die;
  - ack't pas nadat verzending is gelukt.
- `control/browser_extension/background.js`
  - injecteert `content.js` in ChatGPT-tabs;
  - bewaart/leest de bridge-token uit Chrome local storage;
  - proxy't extension-requests naar `http://127.0.0.1:8765`;
  - heeft een Chrome-alarm/watchdog om de content-scriptverbinding te herstellen.
- `control/browser_bridge.py`
  - luistert uitsluitend op `127.0.0.1:8765`;
  - gebruikt een bearer-token uit lokale configuratie;
  - beheert `/health`, `/discover`, `/enqueue`, `/outbox`, `/ai-outbox`, `/ack`, `/ai-ack` en incidentregistratie;
  - schrijft taskfiles alleen onder gecontroleerde repo-paden;
  - commit/pusht taken best-effort naar `main`;
  - houdt lokale bridge-state en acknowledgements bij.
- `control/validator.py`
  - Pydantic task-schema;
  - alleen `python`, `python3` of `.venv/bin/python`;
  - operations: `health_check`, `pytest`, `python`;
  - Python scripts alleen onder `experiments/` of `control/jobs/`;
  - verbiedt live trading en gevaarlijke command-elementen;
  - infrastructure-taken vereisen een geldige build authorization;
  - research-taken mogen juist geen build authorization hebben.
- `control/edge_hunter/build_gate.py`
  - fail-closed toelatingslaag voor control-plane- en candidate-builds;
  - controleert `control/BUILD_STATE.json` en `control/edge_hunter/warrant_policy.json`;
  - live trading, paid actions en wallet actions blijven uitgeschakeld.
- `control/executor.py`
  - pakt alleen een taak als het taskfile in Git HEAD staat;
  - vereist lifecycle-state `ACCEPTED` voordat uitvoering start;
  - verplaatst pending -> running -> completed/failed;
  - schrijft `RESULT.json`, `stdout.log`, `stderr.log` met hashes;
  - commit/pusht resultaat-evidence best-effort;
  - researchqueue-status blijft autoritatief.

## Lokale services

Bekende systemd-user-services in de werkende installatie:

- `prediction-research-browser-bridge.service`
- `prediction-research-executor.service`
- `prediction-research-lifecycle-supervisor.service`
- `prediction-research-hourly-director.service` (oneshot/timer-achtig; kan tussen runs inactive/dead zijn)
- `prediction-research-kalshi-weather-index-recorder.service`
- `prediction-research-twc-recorder.service`

Een werkende bridge is in WSL bewezen door:

- service `active (running)`;
- listener op `127.0.0.1:8765`;
- `/health` HTTP 200;
- periodieke GETs op `/outbox` en `/ai-outbox` met HTTP 200;
- succesvolle POST `/discover`;
- een volledige health-check taak die via de bridge door de executor liep en als resultaat terug in ChatGPT verscheen.

## Task-lifecycle

1. Assistant zet een taskblok zichtbaar in de chat.
2. Content script vindt het taskblok in een assistant-message.
3. JSON wordt lokaal geparsed.
4. Geldige envelope wordt durable opgeslagen in Chrome local storage.
5. `POST /discover` registreert lifecycle `DISCOVERED`.
6. `POST /enqueue` valideert de envelope en task.
7. Bridge schrijft taskfile, commit de taak en registreert `ACCEPTED`.
8. Executor claimt alleen gecommitte `ACCEPTED` tasks.
9. Executor schrijft resultaat + stdout/stderr + SHA-256 hashes.
10. Resultaat wordt gecommit en best-effort gepusht.
11. Bridge `/outbox` exposeert het resultaat.
12. Extension zet het resultaat in de ChatGPT-composer en verzendt het.
13. Extension stuurt `/ack`; lifecycle wordt `ACKED`.

Voor AI hourly work bestaat een afzonderlijke `/ai-outbox` -> ChatGPT -> `/ai-ack` route. Die route accepteert alleen bundles met expliciete guardrails zoals `direct_executor_route=false`, `live_trading=false`, `paid_actions=false`, `wallet_actions=false`, `openai_api=false`.

## Harde transportles: taak moet zichtbaar zijn

### Geleerd probleem

Een bridge-task die alleen in een intern commentary/toolkanaal staat, wordt door de Chrome-extension niet betrouwbaar gezien. De extension scant de zichtbare DOM van assistant-berichten; niet de verborgen interne model/toollaag.

### Regel

Een bridge-taak is pas werkelijk verzonden wanneer de complete taskmarker en JSON letterlijk zichtbaar staan in de gewone assistant-chattekst die de gebruiker in de ChatGPT-interface ziet.

Als de gebruiker zegt dat hij de taak niet ziet:

- behandel de poging als `NIET VERZONDEN`;
- wacht niet op een resultaat;
- stuur dezelfde taak opnieuw als zichtbare assistanttekst.

## Harde parserles: zichtbare Markdown is geen rauw transportkanaal

Tijdens E014/E014R2/E014R3 bleek dat complexe payloads door de zichtbare-chat/DOM-route fragiel kunnen worden. Waargenomen fouten:

- `TASK_PARSE_FAILURE: Unterminated string in JSON`;
- `Expected ',' or '}' after property value`;
- payload werd voortijdig afgekapt;
- een lokaal gegenereerd Python-script kon na succesvolle transportparse alsnog `SyntaxError: unterminated string literal` bevatten.

De praktische oorzaakklasse is dat de extension `textContent` van gerenderde ChatGPT-assistantberichten scant. De taaktekst reist dus door Markdown/DOM-rendering voordat `JSON.parse()` hem ziet. Complexe embedded code, escapes, quotes en multiline strings zijn daarom veel fragieler dan een eenvoudige health-check envelope.

### Parser-safe regels

- Houd task-envelope zo klein mogelijk.
- Geef de voorkeur aan een bestaand scriptpad boven grote `files[].content` payloads.
- Vermijd embedded multiline broncode wanneer dezelfde wijziging via een reeds bestaand/vooraf gecommit script kan.
- Vermijd geneste quote-constructies en complexe escapes in `files[].content`.
- Vermijd het letterlijk opnemen van bridge start/eind-sentinels in payloadvelden of documentatie binnen dezelfde task; de huidige extractor zoekt de eerstvolgende eindmarker en kan daardoor de buitenste JSON afkappen.
- Test complexe transportwijzigingen eerst met een minimale canary/health-check.
- Transport-pass en script-pass zijn twee verschillende gates: een taak kan correct enqueued worden en daarna nog door Python-syntax falen.

## Bekend probleem: stale parse-incident flooding

### Waarneming

Na meerdere malformed taskblokken bleef de extension oude assistant-berichten opnieuw scannen. Voor dezelfde oude malformed task konden daardoor opnieuw `TASK_PARSE_FAILURE` incidents worden aangeraakt/opnieuw aangeboden. Tegelijk geeft `next_outbox_item()` incidenten voorrang vóór normale task-results.

Effect:

- oude parsefouten blijven zichtbaar terugkomen;
- geldige nieuwe task-results kunnen later in de outbox verschijnen;
- de operator kan ten onrechte denken dat de nieuwe taak faalde terwijl het incident eigenlijk naar een oudere payload verwijst.

### Technische oorzaak in huidige code

`content.js` scant telkens tot de laatste 24 assistant-nodes en heeft wel `processedTaskIds` voor geldige task IDs, maar geen equivalente durable dedupe-set voor parse-fingerprints. Bij een parse-error wordt een incident-ID gemaakt uit een fingerprint van het malformed block en opnieuw naar `/incident` gestuurd. De bridge incident-route update hetzelfde incidentbestand, en `/outbox` loopt incidents vóór normale task-results langs.

### Gewenste fix

- persistente `processedParseFingerprints` of vergelijkbare dedupe in Chrome local storage;
- een malformed assistantblock maximaal één incident laten veroorzaken tenzij de blockinhoud verandert;
- normale completed task-results niet laten verhongeren achter stale incidents;
- incident-prioriteit alleen verhogen voor nieuwe/actieve operationele failures;
- tests toevoegen voor: repeated scan, same fingerprint, changed fingerprint, result fairness, ack gedrag.

Status: bekende reliability-bug; niet verwarren met bridge-connectiviteitsfalen.

## HTTP-statussen correct interpreteren

- `GET /health -> 200`: bridge luistert en kan Git/queue-status rapporteren.
- `GET /` zonder token -> 401`: verwacht, geen probleem.
- `GET /discover` zonder token -> 401`: verwacht; `/discover` is bovendien een POST-route.
- `POST /discover -> 200`: extension bereikt de bridge en task-id is syntactisch geaccepteerd.
- `POST /enqueue -> 400`: meestal exception/Pydantic/envelope-validatiepad; dit is geen bewijs dat de bridge down is.
- `POST /enqueue -> 409`: bridge-level reject/business rule, bijvoorbeeld enqueue-resultaat `ok=false`.
- volledige task `exit_code=0` + result terug in ChatGPT: end-to-end pad bewezen.

## Bewezen werkende canary

`CONTROL-BRIDGE-MINIMAL-E012` gebruikte:

- task class `research`;
- operation `health_check`;
- canonical command `.venv/bin/python experiments/health_check.py`;
- geen file writes;
- geen build authorization;
- `live_trading=false`.

Deze taak eindigde `completed`, exit code 0, en rapporteerde Linux/WSL/Python health terug via de normale result-route. Dit is de referentiecanary voor toekomstige bridge-diagnose.

## Build-authorization les

Volgens het huidige validator/build-gate ontwerp:

- `task_class=research`: geen `build_authorization` toevoegen;
- `task_class=infrastructure`: `build_authorization` verplicht;
- control-plane build gebruikt `mode=control_plane`, `build_kind=control_plane`, niet-lege objective en capabilities-lijst;
- candidate build vereist geldig warrant en candidate-state;
- verboden capabilities omvatten o.a. live trading, order submission, wallet/fund movement, paid actions, credential writes en venue write endpoints.

Een 400 tijdens `/enqueue` kan dus puur schema/authorization zijn, ook als Chrome, token, bridge en WSL perfect werken.

## Git en lokale state

Bridge-side lokale state:

- `~/.config/prediction-research/bridge_token` — lokaal secret; nooit in repo/log/chat zetten;
- `~/.config/prediction-research/bridge_state.json` — bridge tasks/acks/AI acks;
- lokale incidenten onder `~/.local/state/prediction-research/incidents/`.

Git blijft audit trail voor tasks/results/evidence. Push is best-effort: lokale execution-evidence mag niet verdwijnen als remote push faalt. Een lokale `git_head` kan daarom tijdelijk voorlopen op GitHub `main`; remote afwezigheid betekent niet automatisch dat lokale uitvoering niet heeft plaatsgevonden.

## Securitygrenzen

- localhost-only bridge;
- bearer-token vereist behalve health;
- alleen gewapende ChatGPT-conversatie;
- validator is authoritative, niet de assistanttekst;
- executor voert alleen toegestane binaries/paths uit;
- live trading hard uit;
- paid actions hard uit;
- wallet/fund actions hard uit;
- geen OpenAI API nodig voor de bridge;
- secrets nooit in repo, task payload of user-visible logs.

## Operationele diagnosevolgorde

Bij twijfel over de bridge, diagnoseer in deze volgorde:

1. systemd bridge service actief?
2. `127.0.0.1:8765` luistert?
3. `/health` 200?
4. extension pollt `/outbox` en `/ai-outbox`?
5. taskmarker werkelijk zichtbaar in assistant-chat?
6. `/discover` 200?
7. `/enqueue` status + exacte response?
8. taskfile pending/running/completed/failed?
9. lifecycle ACCEPTED/RUNNING/COMPLETED/FAILED/DELIVERED/ACKED?
10. result aanwezig in `control/results/<task_id>/`?
11. result via `/outbox` teruggestuurd?
12. Git push gelukt of alleen lokaal gecommit?

Noem de bridge pas `down` als de transport/service-laag faalt. Een parser-, validator-, build-gate- of executed-scriptfout is een andere foutklasse.

## Incidentlog 2026-09-20

### E012 — end-to-end health canary

Status: PASS.

Bewees zichtbare task -> discover -> enqueue -> executor -> result -> ChatGPT.

### E014 eerste poging

Status: TASK_PARSE_FAILURE.

Probleem: complexe embedded Python/multiline content kwam niet als geldige JSON door de zichtbare DOM-transportlaag.

### E014R retry met base64-wrapper

Status: TASK_PARSE_FAILURE.

Probleem: geneste quotes maakten de JSON-string zelf ongeldig in de gerenderde transportvorm.

### E014R2

Status: TASK_PARSE_FAILURE.

Probleem: opnieuw fragiele multiline/embedded-code payload; malformed block bleef daarna als stale parse-incident terugkomen.

### E014R3

Transportstatus: PASS tot executor.
Executionstatus: FAILED.

Resultaat: task werd geaccepteerd en uitgevoerd, maar gegenereerd Python-script faalde met `SyntaxError: unterminated string literal`.

Les: bridge-parser-pass is niet hetzelfde als lokale script-validatie-pass.

### E015

Status: PASS lokaal.

Resultaat meldde `RULE_PRESENT True`, `CHANGED True` en lokale commit `912f5cb...` voor de visible-chatregel in `AGENTS.md`.

Let op: lokale Git kan voorlopen op remote main als push door divergerende geschiedenis faalt. Controleer remote aanwezigheid afzonderlijk voordat wordt gezegd dat GitHub main de wijziging al bevat.

## Onderhoudsregel voor agents

Bij ieder nieuw bridgeprobleem:

1. classificeer de laag: UI/visibility, parser, extension transport, localhost/auth, envelope/schema, build gate, Git, lifecycle, executor, script/runtime, outbox, composer-send, ack;
2. leg exacte fouttekst, task-id, datum en bewezen oorzaak vast;
3. leg de fix of gewenste fix vast;
4. voeg een regressietest/canary toe wanneer praktisch;
5. verander geen andere safety gate om een transportprobleem te omzeilen;
6. update dit document zodra de oorzaak is bewezen of de hypothese verandert.

Doel: de bridge moet cumulatief leren van failures in plaats van dezelfde failure mode opnieuw te introduceren.
