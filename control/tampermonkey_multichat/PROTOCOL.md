# Prediction Chat Multi-Chat Bridge Protocol

Status: canonical
Protocolversie: 0.3.5+
Vastgelegd: 2026-09-23

## Doel

Dit document beschrijft het actuele protocol waarmee een ChatGPT-sessie via Tampermonkey opdrachten naar de lokale WSL Prediction control-plane stuurt en het resultaat naar exact dezelfde ChatGPT-sessie terug ontvangt.

## Architectuur

`ChatGPT assistanttekst -> Tampermonkey -> localhost:8767 command router -> localhost:8766 command receiver -> WSL -> localhost:8765 wake bridge -> oorspronkelijke ChatGPT-chat`

Iedere ChatGPT-tab krijgt automatisch een eigen `chat_id` en `consumer_id`. Een agent hoeft deze IDs niet zelf te verzinnen.

## Actueel commandoprotocol

Gebruik voor lokale bridge-commands gewone zichtbare assistanttekst in dit formaat:

`[[PREDICTION_CMD:<ACTION>:<TASK_ID>]]`

Regels:

- `ACTION` moet door de command receiver zijn toegestaan.
- `TASK_ID` moet uniek zijn voor die uitvoering.
- `<ACTION>` en `<TASK_ID>` zijn uitsluitend documentatieplaceholders en mogen nooit letterlijk worden verstuurd.
- Genereer een echte unieke task-ID, bijvoorbeeld `BRIDGE-PING-20260923-163501-A7K2`.
- Gebruik nooit letterlijke placeholdernamen zoals `UNIQUE_TASK_ID`, `UNIEKE-ID`, `TEST-ID` of `TASK_ID` als task-ID.
- De marker moet letterlijk exact de tekens `[[PREDICTION_CMD:` + action + `:` + task-ID + `]]` bevatten.
- Escape de dubbele punten nooit. Een vorm als `[[PREDICTION_CMD\:BRIDGE_PING\:...]]` is ongeldig voor de parser.
- Voeg geen backslashes, Markdown-escaping of alternatieve scheidingstekens toe aan de marker.
- Stuur de echte commandmarker als één gewone zichtbare assistanttekstregel; niet alleen in commentary/tool-output.
- Gebruik niet automatisch het legacy `PREDICTION_BRIDGE_TASK`-formaat.

De receiver `/health` is autoritatief voor de op dat moment toegestane acties.

## Bridge testen

Wanneer de eigenaar vraagt de bridge te testen:

1. Gebruik `BRIDGE_PING`.
2. Genereer een nieuwe unieke task-ID; hergebruik nooit een eerder gebruikte of voorbeeld-ID.
3. Plaats de commandmarker als gewone zichtbare assistanttekst zonder backslash-escaping.
4. Verklaar de test pas PASS wanneer `RESULT_READY` exact dezelfde task-ID teruggeeft.
5. Voor `BRIDGE_PING` vereist PASS tevens:
   - action = `BRIDGE_PING`;
   - exit code = `0`;
   - WSL-resultaat bevat `BRIDGE_PONG`.
6. Een resultaat met een andere task-ID is geen bewijs voor de huidige test.
7. De Tampermonkey-menuoptie `Bridge-test (PING)` is alleen een diagnostische transporttest en vervangt de zichtbare-DOM-test niet wanneer juist DOM-detectie wordt onderzocht.

## Multi-chat routing

De router op poort 8767 registreert per task-ID de `chat_id` van de sessie die de opdracht creëerde. Resultaten voor een geroute task horen uitsluitend naar die chat terug te gaan.

Autonome, ongeroute wakeups gebruiken alleen de expliciet ingestelde fallback-chat.

## Diagnosevolgorde

Controleer bij uitblijvend resultaat afzonderlijk:

1. Tampermonkey draait op ChatGPT;
2. userscriptversie;
3. poort 8765 wake bridge;
4. poort 8767 command router;
5. poort 8766 command receiver;
6. `/health` van alle drie;
7. DOM-scanner ziet de commandmarker;
8. route bestaat voor de task-ID;
9. resultaat staat in outbox;
10. dezelfde chat consumeert en ACKt het resultaat.

Een gezonde 8765/8766/8767-keten met een ontbrekende commandrequest wijst op de browser/DOM-detectielaag en niet op een WSL-servicefailure.

## Performance-regel

Gebruik geen globale `MutationObserver` die bij iedere streaming DOM-mutatie de volledige conversatie opnieuw scant. De werkende 0.3.5-lijn gebruikt een begrensde periodieke scan van recente conversation roots en vermijdt commandoscanning terwijl ChatGPT actief antwoordt.

## Bewezen baseline 2026-09-23

### Menu/direct transport

Task: `TM-PING-1790173270993`

Resultaat: `BRIDGE_PING`, exit code `0`, `BRIDGE_PONG`, retour naar dezelfde chat.

Status: PASS.

### Automatische zichtbare-DOM-route

Tasks: `TM-DOM-20260923-001` en `DOM-AUTO-20260923-001`

Beide werden als gewone zichtbare assistanttekst verstuurd en kwamen automatisch terug met `BRIDGE_PING`, exit code `0` en `BRIDGE_PONG` in dezelfde ChatGPT-chat.

Status: PASS.

## Canonicaliteit

Wanneer oude sessiekennis of documentatie conflicteert met dit bestand, is dit protocol voor `control/tampermonkey_multichat/` autoritatief.
