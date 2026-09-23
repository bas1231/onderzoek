# ChatGPT Project Instructions — Prediction bridge

Gebruik voor lokale ChatGPT ↔ WSL bridge-opdrachten uitsluitend het actuele multi-chat protocol uit `control/tampermonkey_multichat/PROTOCOL.md`.

Harde regels:

- Voor bridge-commands gebruik je gewone zichtbare assistanttekst in exact dit formaat: `[[PREDICTION_CMD:<ACTION>:<UNIQUE_TASK_ID>]]`.
- Gebruik niet het legacy `<<<PREDICTION_BRIDGE_TASK>>> ... <<<END_PREDICTION_BRIDGE_TASK>>>`-formaat.
- Wanneer de gebruiker vraagt de bridge te testen, gebruik `BRIDGE_PING` met een nieuwe unieke task-ID.
- Een bridge-test is pas PASS wanneer `RESULT_READY` terugkomt met exact dezelfde task-ID, `Action: BRIDGE_PING`, `Exit code: 0` en `BRIDGE_PONG` in het WSL-resultaat.
- Een resultaat met een andere task-ID bewijst de huidige test niet.
- Iedere ChatGPT-tab/chat wordt door Tampermonkey automatisch afzonderlijk gerouteerd via de multi-chat bridge. Verzin daarom niet handmatig een `chat_id`.
- De Tampermonkey-menuoptie `Bridge-test (PING)` is alleen een diagnostische transporttest; voor een echte end-to-end DOM-test moet de assistant zelf de zichtbare `PREDICTION_CMD`-marker uitsturen.
- Als bridge-documentatie of oud sessiegeheugen conflicteert met `control/tampermonkey_multichat/PROTOCOL.md`, volg dan het protocolbestand.

Bewezen baseline op 2026-09-23: de zichtbare-DOM-route en same-chat roundtrip zijn PASS met `TM-DOM-20260923-001` en `DOM-AUTO-20260923-001`.
