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

## Regels voor nieuwe entries

Voeg per incident toe: datum, task-id, foutlaag, exacte foutklasse, bewezen oorzaak versus hypothese, impact, fix/preventie, regressieteststatus en of de oplossing alleen lokaal of ook op remote main staat.
