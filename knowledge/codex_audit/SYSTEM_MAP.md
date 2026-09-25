# Geobserveerde systeemkaart

Bron: werkboom op HEAD `6b33058` plus vooraf bestaande staged/unstaged wijzigingen; individuele hashes staan in `evidence/baseline_manifest.json`. Geen conclusies uitsluitend uit bestandsnamen.

## Hourly en Director

1. Geïnstalleerde `prediction-research-hourly-director.timer`: elk heel uur, `Persistent=true`.
2. Service in `prediction_research_prod`: `runtime_sync.py` preflight → `edge_hunter_cycle.py` → `runtime_health.py`.
3. `runtime_sync.sync`: vereist main en lege index; classificeert wijzigingen, synchroniseert/checkpoint Git. Actueel receipt blokkeert op bestaande index.
4. `edge_hunter_cycle.main`: roept `hourly_cycle.main` aan; rc=75 is bewuste cooldown; andere foutcodes blokkeren. Daarna Edge Hunter prepare, asset- en KWI-checkpoint, Git-checkpoint, gecorreleerde receipt.
5. `hourly_cycle`: cadence → bootstrap/packets → public source sweep → extract/quality → market-instance scan → role routing/recon → Git-memory → candidate queue → hydrate → orchestrate → evidence/failure graph → task schedule → proof review → AI bundle → wake. Extractie heeft een `except Exception: pass`; gevolgen niet als afzonderlijk gereproduceerd defect gepromoveerd.
6. AI bundle/request via `ai_handoff`, `ai_work_exchange`, `git_ai_exchange`; exchangebranch `ai/runtime-exchange`, browserfallback. Geen OpenAI API-director in dit pad.
7. `ai_response_receiver.receive`: run-ID/token/rollen/candidate-authority → validatie/mutatieplan → pending response → packets/candidates/receipt → finale response → orchestration. Identieke retries reconstrueren orchestration. Meerdere bestanden vormen geen bewezen transactie; crash-/concurrentiesafety buiten de geteste gevallen blijft beperkt.
8. Reports: `hourly-reports/`, `knowledge/runs/`; geheugen: `knowledge/research_os/`, `knowledge/recon/`, candidates. Git-checkpoint gebruikt allowlist. Executor heeft daarnaast een eigen Git-write/pushpad; auditor heeft die productiepaden niet uitgevoerd.

## Agents

`agents/registry.json` v4 bevat zes permanente **rollen**, geen bewijs van zes onafhankelijke modelprocessen: discovery (incl. recon/market scan), market_research (weather/behavior/informed flow), mechanics (settlement/microstructure), algebra, red_team_pentest, research_director. Independent_reproducer is tijdelijk en wordt bij serieuze survivors aangemaakt.

Trace van vijf responses op 24 september: alle zes role_results bestaan, corresponderende packets hebben ai_result/applied_at en er zijn receipts/bundles. Statussen verschillen: WAITING_FOR_DATA/RESULT zijn geen voltooid inhoudelijk onderzoek. Externe modelinvocatie/providertrace en onafhankelijkheid zijn niet bewezen door een JSON-rolelabel. Registry, scheduler, responsecontract en downstream packets zijn afzonderlijk gelezen.

## Twee bridgepaden

- Legacy/research bridge: browser extension → `control/browser_bridge.py` / core → validator/build authorization → committed task → `control/executor.py` → RESULT/logs/lifecycle → outbox/ACK. `control/tasks/{pending,running,completed,failed}` en lifecycleledger bewaren status. Supervisor signaleert stalls; hij beëindigt een lopende taak niet.
- Actuele multi-chat: zichtbare assistanttekst/DOM → Tampermonkey → lokale router 8767 → geïnstalleerde command_receiver 8766 → begrensde commands/WSL → wake-server 8765 → oorspronkelijke chat/consumer → ACK. Router bewaart routes exclusief maar niet volledig atomair bij bestaand corrupt bestand. Installed receiver ligt buiten canonical repo; alleen read-only onderzocht, niet geactiveerd.
- Bronbestanden en geïnstalleerde artefacten zijn niet overal gelijk. Op disk installed userscript verschilt van Git; browsergeladen versie blijft onbekend. Een echte DOM-roundtrip is niet uitgevoerd; geen marker is als taak verzonden.

## Weather en marktdata

- TWC recorder: publieke weather.com/Kalshi METAR-weekpayload → SHA256 raw `.bin` → manifests met revisies/statusvergelijking. Receipt-tijd is foutief request-start.
- KWI recorder: drie sequentiële public live_data fetches → city SHA256 raw JSON → gecombineerd manifest; één request-starttijd voor alle steden.
- E369: eerdere complete KWI als persistence, incomplete stationmean als voorspeller, eerste complete city×t als target; dev-afgeleide mechanismepreregistratie. Geen aangetoonde 1–4 uur final-TWC-probabilistische runner.
- E401 supervisor → discovery/capture-cycle manifests → authenticated read-only websocket snapshot/delta/trade → raw/event NDJSON → sequence per subscription → `load_capture`/linker → reactieclassificatie. OrderBook controleert bewust niet meer per-ticker seq+1; subscriptiontracker doet dit.
- Linker gebruikt city/local-hour, IANA timezones, gegroepeerde buckets en primary/revision onderscheid. Volledige DST fold/rule-versie-integriteit niet bewezen.
- Ruwe bestanden onder lokale state, buiten Git; manifests/hashreferenties in onderzoek. Twintig raw-hashchecks slagen. Dit bewijst geen ontvangsttijd of settlementequivalentie.
- Weather/E401/lifecycle units wijzen nog naar afzonderlijke `prediction_research`; hourly/executor naar prod. Permanente collectors zijn niet herstart of verwijderd.

## Grenzen en failurepaden

Validator begrenst executables, relatieve werkdirectories, scriptpaden en buildcontracts. Executor controleert committed task/support provenance, cadence en policy, en voert zonder shell uit. Timeout met bytes-output crasht in foutafhandeling. Legacy failure-recording schrijft INFRA_ERROR maar reconcileert lifecycle niet. Resultaatstatus is geen bewijs van succesvolle remote persistence.

Actuele runtime-inspectie via systemd-userbus en sockettests is sandbox-blocked. Lokale receipts/raw files blijven leesbaar. Geen credentials gelezen, geen queues hervat, geen netwerkmutaties of push uitgevoerd.

## Actuele hervattingsstatus — 25 september 2026

Baseline 80a5ff7 is geverifieerd en veilig. Oudere tekst over ontbrekende baselinecommit is historisch; vervolgcommits/lease blijven geblokkeerd door read-only .git. Productie ongewijzigd. Zie FINAL_AUDIT_REPORT.md en remediation/TRIAGE.md: 20 bevindingen, 64 auditchecks geslaagd op voorstelbron; brede suite en duurzame replay beide 447 passed / 8 failed. Geen productie-FIXED/RETESTED. Frozen acceptancecriteria zijn niet versoepeld. Exact vervolg staat in CONTINUATION.
