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

## Regels voor nieuwe entries

Voeg per incident toe: datum, task-id, foutlaag, exacte foutklasse, bewezen oorzaak versus hypothese, impact, fix/preventie, regressieteststatus en of de oplossing alleen lokaal of ook op remote main staat.
