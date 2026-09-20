# Bridge Incident Ledger

Doel: append-only overzicht van concrete browser-bridge failures en lessen. Gebruik `control/BRIDGE_ARCHITECTURE_AND_LESSONS.md` voor de volledige architectuur en actuele regels.

## 2026-09-20 — VISIBLE_CHAT_NOT_USED

- Laag: UI / visibility.
- Symptoom: assistant dacht een bridge-task te hebben verstuurd, maar gebruiker zag geen taskblok in de gewone chat.
- Oorzaak: taskmarker stond alleen in een interne commentary/tool-laag; `content.js` scant zichtbare assistant-DOM.
- Les: onzichtbare marker = NIET VERZONDEN.
- Preventie: bridge-task altijd letterlijk als gewone zichtbare assistant-chattekst uitsturen.

## 2026-09-20 — E014 TASK_PARSE_FAILURE

- Laag: parser / rendered transport.
- Symptoom: `SyntaxError: Unterminated string in JSON`.
- Oorzaakklasse: complexe multiline embedded Python in `files[].content` over een Markdown/DOM textContent transport.
- Les: minimale envelope; liever bestaand scriptpad; embedded broncode parser-safe houden.

## 2026-09-20 — E014R TASK_PARSE_FAILURE

- Laag: parser / quoting.
- Symptoom: `Expected ',' or '}' after property value in JSON`.
- Oorzaak: geneste quotes in een base64-wrapper maakten de JSON transportvorm ongeldig.
- Les: base64 lost niets op wanneer de wrapper zelf quote-fragiel is.

## 2026-09-20 — E014R2 TASK_PARSE_FAILURE

- Laag: parser / multiline payload.
- Symptoom: `Unterminated string in JSON`.
- Oorzaakklasse: opnieuw complexe embedded code; de DOM-vorm week af van de bedoelde rauwe JSON.
- Les: zichtbare Markdown is geen gegarandeerd byte-identiek JSON-kanaal.

## 2026-09-20 — STALE_PARSE_INCIDENT_REPLAY

- Laag: extension scanning / outbox fairness.
- Symptoom: oude parse-incidents verschenen opnieuw nadat nieuwere geldige tasks waren verstuurd.
- Oorzaak: `content.js` scant steeds recente assistant-berichten; parse-fingerprints hebben geen processed/dedupe-set zoals geldige task IDs. `/outbox` behandelt incidenten vóór normale completed results.
- Effect: stale incidents kunnen nieuwe geldige resultaten tijdelijk overschaduwen.
- Gewenste fix: persistent dedupe van parse-fingerprints + fairness tussen incidents en completed results.

## 2026-09-20 — E014R3 EXECUTION_SYNTAX_FAILURE

- Laag: local script/runtime.
- Transport: bridge task bereikte executor.
- Symptoom: Python `SyntaxError: unterminated string literal` in gegenereerd jobscript.
- Les: transport-validatie en script/runtime-validatie zijn afzonderlijke gates.

## 2026-09-20 — E012 END_TO_END_CANARY

- Laag: volledige keten.
- Status: PASS.
- Bewijs: canonical health-check task eindigde exit code 0 en result kwam via de bridge terug in ChatGPT.
- Gebruik: referentiecanary bij toekomstige twijfel over end-to-end werking.

## 2026-09-20 — E015 VISIBLE_CHAT_RULE_PERSISTED_LOCAL

- Laag: documentation/control-plane.
- Status: PASS lokaal.
- Resultaat: `RULE_PRESENT True`, `CHANGED True`, lokale commit `912f5cb...`.
- Let op: remote GitHub main kan achterlopen bij push-divergentie; verifieer remote apart.

## 2026-09-20 — E016 CHAT_ACK_STALL

- Laag: result delivery / acknowledgement.
- Symptoom: lifecycle bleef `DELIVERED`; watchdog meldde `CHAT_ACK_STALL` na ongeveer 208 seconden met detail `Resultaat werd aangeboden maar niet tijdig ACKED.`
- Bewezen gedrag in `content.js`: `pollOutbox()` klikt eerst het ChatGPT-sendknopje via `insertAndSend()`, wacht 1 seconde en doet daarna `POST /ack`.
- Belangrijk defect: de returnwaarde van `POST /ack` wordt niet gecontroleerd; de code logt daarna altijd `result returned`, ook als ACK faalt of niet wordt opgeslagen.
- Waarschijnlijke failure modes: tijdelijke localhost/extension-fout tijdens ACK, ACK-response niet-ok, of te vroege ACK-semantiek rond UI-send. Exacte oorzaak van dit concrete incident is nog niet bewezen.
- Impact: het resultaat kan zichtbaar in ChatGPT zijn terwijl de bridge lifecycle niet naar `ACKED` gaat; watchdog genereert dan een incident en dezelfde outbox-item kan opnieuw aangeboden worden.
- Gewenste fix: controleer `ack && ack.ok`, retry ACK met bounded backoff, bewaar pending ACKs durable, en log/incident onderscheid tussen `CHAT_SEND_FAILED`, `ACK_HTTP_FAILED` en `ACK_REJECTED`.
- Regressietest: task-result zichtbaar versturen, bridge tijdelijk ACK laten falen, herstellen, en bewijzen dat durable retry uiteindelijk exact eenmaal naar `ACKED` gaat zonder result starvation.
- Status: OPEN; documentatie remote main bijgewerkt. Geen live/paid/wallet impact.

## 2026-09-20 — E016 RESULT_LATER_DELIVERED

- Laag: end-to-end result delivery.
- Status task: PASS (`exit_code=0`).
- Resultaat: `RULE_PRESENT=True`, `CHANGED=False`, `HEAD=c60504d...`.
- Interpretatie: de visible-chatregel stond al in `AGENTS.md`; E016 was idempotent en hoefde niets meer te wijzigen.
- Het eerdere `CHAT_ACK_STALL` blokkeerde de uiteindelijke zichtbare levering niet: het normale E016-resultaat verscheen later alsnog in ChatGPT.
- Belangrijk: dit bewijst niet dat de ACK-reliability-bug is opgelost. Het bewijst alleen dat delayed delivery/retry uiteindelijk werkte voor dit concrete resultaat. De ACK-fix blijft OPEN totdat response-validatie en retry-regressietest zijn gebouwd en geslaagd.

## 2026-09-20 — E017 TASK_PARSE_FAILURE

- Laag: zichtbaar-chat transport / JSON parser.
- Symptoom: `Expected ',' or '}' after property value in JSON` rond positie 234.
- Bewezen oorzaak: `files[].content` bevatte opnieuw letterlijke dubbele quotes uit het embedded Python-script. In de gerenderde assistant-DOM kwamen die quotes niet JSON-escaped bij de extension aan, waardoor de outer envelope ongeldig werd.
- Impact: E017 bereikte `/enqueue` en de executor niet; er is dus geen ACK-retrycode gewijzigd door deze poging.
- Les: voor bridge file-write payloads mag `files[].content` niet afhankelijk zijn van JSON-escaping van dubbele quotes of complexe multiline broncode. Gebruik bij voorkeur een minimale, éénregelige, parser-safe Python bootstrap met alleen single quotes of voer bestaande lokale code uit.
- Preventie: volgende retry gebruikt een korte single-line Python job zonder letterlijke dubbele quotes in `content`; daarna aparte runtime/syntaxvalidatie.
- Status: OPEN; failure remote gedocumenteerd, fix nog niet bewezen.

## 2026-09-20 — E019 OUTBOX_FAIRNESS_PATCH_FAILURE

- Laag: lokale patchgenerator / Python syntax.
- Task: `CONTROL-BRIDGE-OUTBOX-FAIRNESS-E019`.
- Symptoom: `SyntaxError` in gegenereerde `control/browser_bridge.py` op `if task_id not `in tracked_tasks:`.
- Bewezen oorzaak: de base64-bron voor de vervangende `next_outbox_item()` bevatte één verdwaalde backtick vóór `in`; de fout zat dus in de gegenereerde patchtekst, niet in de bestaande bridge.
- Veilig gedrag: de patchjob detecteerde de syntaxfout via `py_compile`, herstelde daarna de oorspronkelijke `browser_bridge.py` en herstelde/verwijderde ook de tijdelijke test. Er is geen defecte fairness-code gecommit.
- Les: ook base64-bootstrapcode moet vóór verzending lokaal syntactisch worden gegenereerd/gevalideerd; transportveilig betekent niet automatisch broncode-correct.
- Vervolg: E019R gebruikt opnieuw gegenereerde en vooraf geparste Python-bron plus dezelfde regressie-eis: met tegelijk een normaal resultaat en een incident komt eerst het normale resultaat, daarna het incident.
- Status: FAILED_SAFE; fairness-fix nog niet geïmplementeerd.

## 2026-09-20 — E019R CHAT_ACK_STALL_AFTER_E017R

- Laag: runtime activation / acknowledgement.
- Task: `CONTROL-BRIDGE-OUTBOX-FAIRNESS-E019R`.
- Symptoom: watchdog meldde opnieuw `CHAT_ACK_STALL` terwijl lifecycle al `DELIVERED` was, ongeveer 180 seconden na aanbieding.
- Belangrijk bewijs: E017R had de durable ACK-retrycode succesvol in `control/browser_extension/content.js` geschreven en syntactisch gevalideerd, maar dit incident toont dat die bronwijziging op zichzelf niet voldoende bewijs is dat de reeds draaiende browser-extension/runtime de nieuwe code daadwerkelijk gebruikt.
- Exacte oorzaak: nog niet bewezen. Mogelijkheden zijn onder meer dat de bestaande content-scriptinstantie nog oude code draaide, dat de extension niet opnieuw geladen was, of dat de ACK-route ondanks de nieuwe code nog een andere failure mode heeft.
- Les: voor browser-extensionfixes zijn vanaf nu twee afzonderlijke gates nodig: `SOURCE_VALIDATED` en `RUNTIME_ACTIVATED_AND_PROSPECTIVELY_PROVEN`.
- Status E017R: source fix PASS, runtime effect nog UNPROVEN.
- Status E019R: het normale task-resultaat was door de bridge aangeboden (`DELIVERED`), maar de uiteindelijke taskstatus moet uit het normale E019R-resultaat worden gelezen; dit incident alleen zegt niet of de fairness-regressietest PASS of FAIL was.

## Regels voor nieuwe entries

Voeg per incident toe: datum, task-id, foutlaag, exacte foutklasse, bewezen oorzaak versus hypothese, impact, fix/preventie, regressieteststatus en of de oplossing alleen lokaal of ook op remote main staat.
