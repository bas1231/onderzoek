# DIRECT_SOL — reparatie en concrete blokkade

Peilmoment: 2026-10-09T07:40:21Z. Campagne `FULL-A2Z-LIVE-20261004-V4`, kandidaat `AUTO-DISCOVERY-54d13314c7879b58e46d`.

**Geen A→Z-PASS en geen nieuwe Sol→Astra-roundtrip.** R4P4 is nu bytegetrouw gedeeld. Het bestaande transport kan een opdracht klaarzetten, maar de bedoelde browserchat haalt het event niet op. Modelidentiteit en nieuwe modeluitvoering zijn niet bewezen.

## Gevonden hoofdoorzaak

E234 was geen modelhandoff: de task bevatte alleen Python die lokaal task-ID, target-modelveld en prompt-SHA controleerde en `SOL_REQUEST_VALID` printte. Er was geen GitHub-publicatie, Sol-sessiestart, promptlevering, inference of resultaatregistratie. Het executor-PASS bewees precies die drie assertions. De schema-validator heeft zelf geen modeluitvoerder.

De application-runner in `patch_e106_gate.py` maakt na Astra REVISE een lokaal `direct_requests/<task>.json` en een exportbestand. Dat publiceert niets naar GitHub en activeert geen Sol-worker. `direct_sol_record.py` normaliseert reeds aangeleverde tekst naar runbestanden; de daarin gemaakte events zijn afgeleide normalisatie, geen door een modelprovider waargenomen events. `materialize_direct_sol.py` importeert resultaten maar roept geen model aan.

R4P4 ontbrak bij aanvang op GitHub (404). Deze eerste ontbrekende stap is hersteld met commit [974466a](https://github.com/bas1231/onderzoek/commit/974466ab45ca26443f3aa8b7b48b0de91915ba60); de bytes zijn exact gelijk aan de bestaande WSL-aanvraag. De volledige Astra R4P3-feedback is behouden.

## A02 en historische modeluitvoering

A02 eindigde met exit 2 / AssertionError in de voorbereidingscode, vóór de modelrunner. De code verwachtte `model_policy` of `target_model` in het Astra-request, terwijl dat request een `phase` bevat en de runner de policy daaruit afleidt. Er bestaat geen geldig A02-infrastructuurreviewresultaat om te hergebruiken.

De eerdere Sol-bestanden zijn onderzocht en behouden:

| Record | Gecontroleerde uitkomst |
| --- | --- |
| R4P1 | Ongeldige completion-SHA; R4P2 noemt expliciet deze serialisatie-retry. Niet hergebruiken. |
| R4P2 | Bestaande schema- en hashchecks geldig. |
| R4P3 | Bestaande schema- en hashchecks geldig; reguliere Chat-identiteit staat als metadata in het resultaat. |
| R5P1 | Bestaande schema- en hashchecks geldig; reageert op R4P2-feedback en vervangt de latere R4P3→R4P4-revisie niet. |

Git toont afzonderlijke request/result-publicaties en latere projectexecutor-materialisatietaken. Voor R4P3 zijn dat requestcommit `5e67bc5`, resultcommit `1f75f0c`, materialisatie `c1e4f98` en dispatch `2b1c3ad`. Voor R5P1: request `d927d04`, result `6fd3b2e`. Dat bewijst de opslag- en importroute, niet zelfstandig de oorspronkelijke modelkeuze of automatische sessieactivering. Er is geen provideruitvoering uit deze zelfbeschrijvende metadata verzonnen.

De eerdere echte Astra R4P3-review is bewaard:
- task: `A2Z-V4-ASTRA-PREBUILD-DIRECT-20261008-R4P3`;
- geselecteerd model en Codex-command: `gpt-6-astra`, `-m gpt-6-astra`;
- thread: `01a11c78-9493-7ec3-b4de-eea99cac382c`;
- completion-SHA: `cf9927282987bbb0120e4b7781b5344e128594aae1999abaadf832cc6cead49e`;
- besluit: **REVISE**. Geen heruitvoering gedaan.

## Uitgevoerde reparatie en tests

[Draft-PR #54](https://github.com/bas1231/onderzoek/pull/54) bevat uitsluitend:
- `control/model_execution/direct_sol_delivery.py`;
- `tests/model_execution/test_direct_sol_delivery.py`.

De adapter bindt request, immutable commit, bestandhash, prompthash en route; bewaart een immutable intent; gebruikt de bestaande continuation-API; voorkomt dubbele logische verzending; geeft expliciete capabilityfouten; behandelt ACK/DONE niet als modelcompletion.

Broncommits: `3ed7c5637003dbc28f8fe8d26ba8065d3163fbba`, `39691294e51b4bda63f62c442e24224fcee2aad2`. Testcommits: `4112c3134b432a08e406a2a78015ce45c4db3c67`, `69f32b0771ac525aaccd5376503988f21aca5506`. De PR is niet gemerged of permanent geïnstalleerd.

Via de bestaande GitHub-command-bus en capability-scoped projectexecutor:
- D01: geïsoleerde scopelease geregistreerd; geen andere actieve builder.
- D02: **17 regressies PASS**, publicatiebytes en inputhash gelijk; historische resultchecks en A02-fout bevestigd. Lokale commit `f8b5e0802f15d9f5b115a7faa8987c13fe3acdbb`.
- D03: echte externe-continuation-aanroep faalde op runtime-write buiten taskroots.
- D04: **18 regressies PASS**, inclusief de nieuwe permission-regressie. Met app-status in de toegestane worktree werd de bestaande runtime-enqueue expliciet geprobeerd: de guard blokkeerde `prediction-chat-bridge/continuations/.CONT-0259c2837282ed9d1e234a0f…tmp`. Geen continuation aangemaakt. Dit is een bewezen capabilitygrens, geen model-PASS.
- D05: bestaande `auto_continue:true`-route naar de eerdere Sol-chat gebruikt. Executor-PASS valideert uitsluitend de gepubliceerde aanvraag. De brontaak bevat de volledige workerinstructie en immutable requestreferentie; er is nog geen bewijs dat Sol die heeft gelezen.

De 18 tests bestrijken onjuiste bestand-/prompthashes, verkeerde/ontbrekende route, mutable branchreferenties, taakpadvalidatie, gewijzigde publicatie onder hetzelfde ID, idempotentie, crashherstel, timeoutstatus, permissionweigering en het onderscheid tussen transport en modelcompletion. Dit zijn geen experimenttests of metingen. Volledige logs: [EXECUTOR_RESULTS.json](EXECUTOR_RESULTS.json).

## Echte bezorgpoging en resterende blokkade

D05 is `DEV-PRED-DIRECTSOL-R4P4-MODEL-HANDOFF-20261009-D05`.
- route: `SESSION-ROUTE-246799adf99f0bf8336c27a0`;
- chat: `chat-c-9e3bfb0d-10`;
- event: `1791531149-cd0bb37bd857`, aangemaakt 2026-10-09 07:32:29 UTC;
- bij laatste observatie: **outbox**, niet inflight/sent; geen continuation of workerantwoord;
- GitHub R4P4-resultaat en worker-BLOCKED-record: afwezig (404).

Er zijn twee onderscheiden grenzen:
1. De directe application-Python continuation-aanroep mag onder de huidige executor-guard niet naar de bridge-runtime schrijven. `write_runtime` staat expliciete `install_runtime` toe, geen willekeurige child-Python runtime-writes. Geen guardversoepeling, nieuwe service om de guard te ontwijken of directe queue-injectie gedaan.
2. Het toegestane source-backed `auto_continue`-pad is wel verstuurd, maar vereist dat de bedoelde ChatGPT-browserchat pollt. Er is geen geregistreerde dashboard-launcher; de betreffende directories ontbreken. De bestaande launcher/consumer selecteert of attesteert bovendien geen GPT-model of Chat/Work-modus.

Minimale interventie zonder bridgewijziging: open/activeer de eerdere **reguliere GPT-5.6 Sol-chat** waarin R4P3/R5P1 zijn gemaakt, met de bestaande wake-bridge actief en feitelijk GPT-5.6 Sol geselecteerd. D05 staat al klaar; **niet opnieuw dispatchen**. Als alleen een nieuwe chat beschikbaar is, moet die eerst haar eigen bewezen SESSION-ROUTE krijgen; de oude route mag niet worden voorgesteld als die nieuwe chat.

Voor onbeheerde activering en controle van de juiste modelervaring is eerst specifieke toestemming nodig voor een begrensde wijziging aan de bevroren browseractivering/modelattestatie. Voor de directe callback-adapter zou daarnaast een expliciete typed executor-operation nodig zijn; geen algemeen runtime-write-recht. De huidige D05-route vereist die executorwijziging niet.

## Actuele lifecycle en acceptatie

| Stap | Stand |
| --- | --- |
| Governed R4P4 gemaakt en input gebonden | Bestaand checkpoint, behouden en gevalideerd |
| Immutable gedeelde request | Hersteld en bytegetrouw teruggelezen |
| Activering juiste Sol-worker | Geblokkeerd bij browserontvangst/verifieerbare modelidentiteit |
| Nieuw inhoudelijk Sol-resultaat | Niet aanwezig |
| Resultaat/provenance import | Niet uitgevoerd zonder nieuw resultaat |
| Nieuwe Astra PREBUILD | Niet gestart zonder nieuw Sol-resultaat |
| Automatische REVISE/APPROVE-vervolglus | Niet bewezen |
| Exacte build en Astra POSTBUILD | Niet bereikt |
| Tests/meting/supervisor/eindrapportage | Experimentele uitvoering blijft geblokkeerd |

Laatst bewezen inhoudelijk checkpoint: **Astra R4P3 PREBUILD = REVISE**. R4P4 wacht op echte Sol-uitvoering. **NO_PROVEN_EDGE** blijft gelden.

Geen bevroren bridge-/executorbron gewijzigd; vier kritieke geïnstalleerde hashes zijn vóór/na gelijk bevonden. Geen betaalde API, credentials, live trades, wallets of WSL Git-push gebruikt. Geen nieuwe service/timer gestart. Scopelease afgesloten; taak-/test-/foutevidence behouden. D05 blijft als één geautoriseerde, nog niet geleverde taak klaarstaan.
