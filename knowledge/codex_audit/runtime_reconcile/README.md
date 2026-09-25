# Deploymentreconciliatie — 2026-09-25

Status: **AUDIT_INCOMPLETE + RESIDUAL_RISK**. Canonical reparaties blijven FIXED_AND_RETESTED; runtime deployment nog niet uitgevoerd vanuit deze sandbox. Wetenschap: afzonderlijk **NO_PROVEN_EDGE**.

## Bewijs en semantische beoordeling

`preservation_manifest.json` bewaart HEAD, indexhash, hashes van bestaand ownerwerk en alle vijf target-/bronhashes. `before/` bewaart exacte deployed bron; `diffs/` de volledige deltas; `payload/` de beoogde bron. Iedere target matcht byte-voor-byte de vastgelegde canonical vóór-reparatiebasis. Geen conflicterende ownerwijziging in deze vijf targets aangetroffen. De routerbasis bevat reeds consumer-routing; die logica blijft behouden. Dit is toepassing van de bewezen delta op een identieke basis, geen blinde keuze voor een complete branch.

| Target | Uitsluitend geïntegreerde reparatie |
|---|---|
| command_router.py | Corrupte routes weigeren; framing/envelop valideren; malformed upstream HTTP200 en transportfout zichtbaar afhandelen |
| kalshi_weather_index_recorder.py | Requeststart en daadwerkelijke ontvangst per response scheiden |
| twc_hourly_recorder.py | Ontvangst na responsebody registreren |
| market_reaction.py | Coveragegaten, ontbrekende executable prijzen, vreemde ticker en niet-eindige prijzen niet als bewezen reactie behandelen |
| evaluate_kwi_full_station_checkpoint_e369.py | Receiptsemantiek, targetchronologie en configidentiteit afdwingen |

Installed userscript/browser-loaded bron is niet in deze vijf targets opgenomen; drift blijft apart ongekwalificeerd. Geen eigenaarbron daarvan overschreven.

## Testresultaten

- `tests/payload_tests.log`: **128 passed**, exact voorbereide payload in geïsoleerde bronboom, inclusief PIT/weather/router/evaluator en bestaande audit-/agentcontracten.
- `tests_fixture_missing_dependencies/`: eerste harnesspoging 118 passed, 2 failed, 8 errors. Oorzaak: reproductiehelpers en agentcontracten niet gekopieerd. Harness aangevuld; geen testassertie of productiebron aangepast.
- `runner_tests.log`: **4 passed**, deploymentfixture, idempotentie, ownerconflict, rode testgate en gewijzigde index. Systemctl gemockt.
- `relevant_regression.log`: aanvullende runtime-sync/checkpoint/cadence- en runnersafetytests. Dit zijn fixtures, geen werkelijk hervatte hourly-run.
- Eerdere externe128/4 en canonical475 blijven geldig binnen hun scope; aantallen overlappen en worden niet opgeteld tot unieke coverage.

## Hourly: causale diagnose en harde grens

De actuele sync-receipt meldt BLOCKED wegens niet-lege index. `runtime_sync.py:177` weigert staged wijzigingen; `main()` retourneert vervolgens **2**. De unit (`hourly_unit.txt`) heeft `SuccessExitStatus=75`, uitsluitend voor een intentionele cooldown/no-work-cyclus. Exit2 is dus geen75 en preflightfailure voorkomt ExecStart. Een failed-service bij deze bescherming is verwachte fail-closed werking, geen bewijs dat de bronfix ontbreekt. Geen aanleiding om2 als succesvolle research te maskeren.

Canonical HEAD50ef287 verschilt van lokaal opgeslagen origin/main8c92519. Zonder fetch is actuele remotestand niet bewezen. Het syncpad kan daarnaast onverwachte tracked wijzigingen weigeren en lokale ahead/divergentie blokkeren. De eerste daadwerkelijk aangetoonde blokkade is de ownerindex; vervolgblokkades zijn statisch onderbouwd, niet door een verboden workflow uitgeprobeerd. `git_checkpoint.py:301` bevat een echte push. Daarom geen sync/hourly/checkpoint aanroepen, geen index leegmaken en geen remote gelijkzetten.

**Nog vereiste beleidskeuze:** moet hourly een expliciet ontworpen, afzonderlijk geautoriseerde lokale/no-push uitvoeringsmodus krijgen, of blijft de bestaande remote-synchrone/pushende workflow gewenst nadat de eigenaar diens werk zelf heeft geïntegreerd? Onder het huidige pushverbod en behoud van staged werk kan deze keten niet veilig hervatten. Dit is geen conflict in de vijf bronbestanden. Er is geen stilzwijgende beslissing genomen.

## Eén begrensde WSL-invocation

Voer `python3 /home/leonh/prediction_research_prod/knowledge/codex_audit/runtime_reconcile/reconcile_wsl.py` uit. Script weigert veranderde bron, payload, routerunit, drop-ins, index of vastgelegd ownerwerk; draait vooraf128 offline +4 tijdelijke sockettests; bewaart per-run backups en vervangt alleen vijf allowlistbestanden atomair per bestand. Geen Gitmutatie, push, API-call, productiequeuebericht, wallet of trade. Alleen de reeds actieve router krijgt `try-restart`; geen andere services/timers worden gestart. Geen algemene destructieve cleanup; tijdelijke pytestbronnen verdwijnen via TemporaryDirectory. Bij gedeeltelijke fout worden verrichte wijzigingen expliciet gelogd en niet automatisch over later ownerwerk teruggedraaid.

Uitvoering vereist een rustig onderhoudsmoment zonder gelijktijdige broneditor/deployer: hashcontroles detecteren wijzigingen, maar vormen geen kernel-CAS-lock tegen niet-meewerkende writers. Atomair per bestand betekent niet atomair over vijf bestanden. Bewijs blijft bij iedere stap behouden. Een mislukte routerrestart blijft BLOCKED_OR_PARTIAL; geen automatische herstartlus.

Het script kan deployment op schijf en beperkte routerherstart kwalificeren, **geen globale productie-E2E-PASS**. Weathercollectoren worden niet aangeroepen/herstart: nieuwe invocaties gebruiken de nieuwe bron, bestaande imports zijn ongeattesteerd. Hourly en browser/Director/queueketen blijven ongekwalificeerd. De externe run wordt onder `external_runs/` vastgelegd; verdere algemene herhaling van de audit is niet nodig.

## Drievoudige conclusiecontrole

1. Bron/provenance: alle deployed targets identiek aan bewaarde vóórbasis; exacte reparatiediffs geïnspecteerd.
2. Reproduceerbaarheid:128 payloadtests groen; deploysafetytests en hourlyguardregressie afzonderlijk vastgelegd.
3. Operationele grens: systemdunit/exitcode/pushpad gecontroleerd; geen nuttige hourlyrun of loaded browsercode verzonnen. Economische promotie is buiten scope en blijft NO_PROVEN_EDGE.


## Nieuwe begrensde hourlykwalificatie

`finalize_hourly_e2e_wsl.py` is nu aanwezig (vervangt de eerdere melding dat geen script was gemaakt). Het is bewust een bereikbaarheids-/guardkwalificatie, **geen volledige E2E-harness**. Draait reeds binnen Codex; niet nogmaals extern nodig.19 focused/affected tests groen in `hourly_qualification_tests.log`. Run `hourly_final_runs/20260925T104639Z-9ff94aea/RESULT.json` bevestigt BLOCKED en owner_preserved=true. Geen originele guard gewijzigd; gitadapter accepteert uitsluitend branchnaam en staged namen, weigert iedere andere operatie. Geen downstreamcyclus gestart en geen PASSpad op basis van mocks. Het gevraagde volledige E2E-doel is niet bereikt. Onder deze uitvoering blijft de exacte index/pushblokkade bestaan.

Veilige lokale commit: `bash knowledge/codex_audit/runtime_reconcile/commit_final_audit.sh`. Script committeert alleen zes auditstatusbestanden en runtime_reconcile (zonder pycache), schakelt hooks uit en controleert de overige staged ownerdiff. Geen push.
