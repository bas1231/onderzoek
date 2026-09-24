# AI exchange cadence + bridge result latency — 2026-09-24

Status: **DIAGNOSED / MITIGATION APPLIED / FOLLOW-UP OPEN**

## Samenvatting

Twee afzonderlijke problemen zijn vastgesteld. Ze mogen niet als één storing worden behandeld.

1. **AI exchange backlog:** de lokale hourly Research-OS runtime publiceert maximaal ongeveer één nieuwe `PVA_AI_EXCHANGE_REQUEST_V1` per actief uur naar `ai/runtime-exchange`. De bestaande ChatGPT-consumers bestonden al (`Prediction Uurrapport slot 2` en `slot 3`), maar draaiden ieder slechts eens per 5 uur en verwerken per run maximaal één oudste geldige pending request. Daardoor kon de consumer-capaciteit structureel lager zijn dan de producer-capaciteit en ontstond backlog.
2. **Bridge result-return latency:** de WSL-taskuitvoering en outbox-route werken, maar een gereed resultaat kan vertraagd terug in de ChatGPT-chat verschijnen. `DEV-PRED-AI-RECENT-AUDIT-E001` kwam uiteindelijk terug als `PASS exit=0 rcs=1:0`; het resultaat was dus niet verloren, maar te laat afgeleverd.

## Bestaande architectuur blijft ongewijzigd

Geen herontwerp van het Research OS. De bestaande keten blijft:

`Scout/Recon -> routing -> six-domain AI work bundle -> Git request -> ChatGPT scheduled worker -> Git response -> local ai_response_receiver -> Director/candidate state`

`Git` blijft canonieke memory/audit trail; `ai/runtime-exchange` blijft alleen transport. Geen OpenAI API, geen betaalde actie, geen live trading, geen wallet/fund action.

## Root cause AI exchange

De AI-consumer was niet afwezig. De scheduled workers waren al ingericht om bij `LOCAL_REQUEST_PENDING` de oudste geldige request te behandelen, alle gevraagde role IDs exact één keer te beantwoorden en create-only een `PVA_AI_EXCHANGE_RESPONSE_V1` naar `ai/runtime-exchange` te schrijven.

Het probleem was cadence/capaciteit:

- producer: tot circa **1 request/uur**;
- oude consumer-cadence: `slot 2` en `slot 3` elk **1 run per 5 uur**;
- per consumer-run: maximaal **1 request**;
- gevolg: backlog kon sneller groeien dan hij werd afgehandeld.

Ondersteunend bewijs: op `ai/runtime-exchange` werd op 2026-09-24 omstreeks 14:10 lokale tijd nog een response geschreven voor `hourly-20260924T070000+0200` (`ai-exchange: service hourly-20260924T070000+0200`, commit `4cbdae6f6de54f3dc6a1a12e1041e0e4f04ede97`), terwijl latere hourly requests al bestonden.

## Toegepaste mitigation

De architectuur en response-contracten zijn niet gewijzigd. Alleen de scheduler-capaciteit is aangepast:

- `Prediction Uurrapport slot 2`: **ieder uur om :10**; normale bestaande Research-OS worker.
- `Prediction Uurrapport slot 3`: **ieder uur om :40**; recovery/overflow worker. Hij verwerkt uitsluitend maximaal één oudste pending AI-exchange request en doet niets als er geen backlog is.

Daarmee is de theoretische service-capaciteit maximaal ongeveer **2 responses/uur** tegenover circa **1 nieuwe request/uur**, zodat bestaande backlog kan worden ingelopen en daarna normaliter geen groei hoort op te treden.

## Bridge result-return bevinding

De bridge-uitvoering zelf is aantoonbaar functioneel:

- task: `DEV-PRED-AI-RECENT-AUDIT-E001`
- uiteindelijk resultaat: `NIGHTSHIFT_WSL_RESULT_V1 ... status=PASS exit=0 rcs=1:0`
- geobserveerde head in compact result: `f3009e8c261bcfe82263c9912db7f26099a30153`

Conclusie: de task is uitgevoerd en het resultaat is uiteindelijk via bridge -> browser -> chat afgeleverd. Het resterende defect is **delivery latency/polling/ACK timing**, niet task loss of WSL execution failure.

## Niet verwarren

- **AI exchange backlog** = scheduled ChatGPT worker-capaciteit/cadence.
- **Bridge latency** = resultaat van een lokale bridge-task verschijnt te laat in de chat.

De AI exchange gebruikt Git als primaire transportlaag en heeft Tampermonkey niet nodig voor normale request -> response verwerking.

## Follow-up / acceptatie

De mitigation is pas volledig bewezen wanneer meerdere opeenvolgende hourly cycli laten zien dat:

1. nieuwe requests binnen dezelfde of eerstvolgende worker-run een geldige response krijgen;
2. pending request count niet verder groeit en bestaande backlog afneemt naar nul;
3. `ai_response_receiver` de responses lokaal valideert en toepast;
4. geen duplicate/conflicting responses worden geschreven;
5. bridge smoke/audit results na gereedkomen binnen seconden tot korte bounded tijd terug in de chat verschijnen, zonder duplicate delivery.

Tot die tijd geldt:

- AI exchange cadence: **MITIGATION APPLIED, MONITORING REQUIRED**;
- bridge execution: **PASS**;
- bridge result-return latency: **OPEN**;
- economic conclusion: **NO_PROVEN_EDGE**.
