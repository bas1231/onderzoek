# Canonical herstel en onafhankelijke kwalificatie — 25 september 2026

## 1. Eindkwalificatie

**AUDIT_FAIL + AUDIT_INCOMPLETE + NO_PROVEN_EDGE.** De geverifieerde brondefecten zijn daadwerkelijk gerepareerd in de canonical werkboom. De volledige operationele keten kan nog niet worden gekwalificeerd: hourly is geblokkeerd/stale, deployment wijkt af, live socket/systemd/browsercontroles zijn beperkt en twee suitefailures blijven expliciet open. Geen AUDIT_PASS_WITH_TESTED_ASSURANCE.

## 2. Executive summary

23 permanente bevindingen: **17 FIXED_AND_RETESTED**, 1 CONFIRMED_OPEN, 1 BLOCKED, 3 RESIDUAL_RISK, 1 UNPROVEN. Eén van de 17 betreft een vóór integratie ontdekte voorstelregressie; het getal is geen telling van 17 afzonderlijke productie-incidenten.

Alle oorspronkelijke **64 auditgedragstests slagen tegen canonical bron**. Definitieve brede canonical regressie: **474 passed / 2 failed**, exit1, 476 tests. Dit is geen volledig groene suite. De twee resterende failures zijn de sandbox-geblokkeerde sockettest en het expliciet onbesliste 15s/600s-policyconflict. Geen skips/xfails toegevoegd, geen veiligheidscriteria versoepeld.

22 code-/testbestanden gewijzigd/toegevoegd; bronbasis exact gecontroleerd tegen proposal_manifest.json. Alle zeventien voorgestelde bestandbases matchten; geen blinde patchtoepassing. Bestaande staged userindex en alle niet-gerelateerde tracked bestanden zijn ongewijzigd. Ook de staged installer is onaangeroerd.

## 3. Exacte scope en Git-basis

Baseline `80a5ff7cfc49b7be27413d0fea9c03b0f48e0f50`; eerdere auditevidence `db6c0f3c98b0b8fbc8b89544c3745cfba311e8e6`. Beide bestaan en zijn niet herschreven. Op db6c0f3 is de canonical werkboom gerepareerd met expliciete autorisatie van de eigenaar ondanks read-only .git. Geen nieuwe canonical commits konden worden gemaakt; dat onderdeel van de missie blijft BLOCKED.

Geen herstart van discovery, geen productiequeue hervat, geen services geactiveerd, geen order/wallet/paid API/netwerkhandel, geen push, geen reset. Historische raw/immutable evidence en holdout zijn niet gewijzigd. Node/pytest-tests gebruiken synthetische data en begrensde lokale fixtures.

## 4. Werkelijk geobserveerde architectuur

Zie SYSTEM_MAP.md. Hourly timer → runtime_sync → edge_hunter_cycle/hourly_cycle → bron/recon/queue → AI-bundle/exchange → responsevalidator → agentpackets/receipt/orchestration → checkpoint. ChatGPT is Director; registry v4 bevat zes permanente rollen plus transient reproducer. Dit bewijst geen zes onafhankelijke LLM-processen.

Multi-chat en legacy researchbridge blijven aparte paden. Hourly/executor wijzen naar prod; weather/lifecycle deels naar legacy checkout. Gerepareerde canonical files zijn niet automatisch geladen door bestaande processen of de browser. Deze deploymentgrens is expliciet behouden.

## 5. Tests uitgevoerd

| Ronde | Resultaat | Evidence onder remediation/ |
|---|---|---|
| Bestaande baseline (voor herstel) | 374 pass / 17 fail | oorspronkelijke test_runs/ |
| Negen auditinvarianten vóór herstel | 9 fail | oorspronkelijke test_runs/ |
| Voorstelreplay | 447 pass / 8 fail | durable_replay.* |
| Canonical weather/PIT focus | 39 pass / 46 deselected | canonical_weather.* |
| Canonical proof focus | 16 pass / 51 deselected | canonical_proof.* |
| Canonical bridge focus | 34 pass / 35 deselected | canonical_bridge.* |
| Canonical executor focus | 20 pass / 42 deselected | canonical_executor.* |
| Eerste volledige canonical suite | 447 pass / 8 fail | canonical_initial_full.* |
| Nieuwe deliverycounterexamples vóór herstel | 5 fail / 2 pass | canonical_delivery_red.* |
| 64 auditchecks plus 7 deliverychecks | 71 pass | canonical_delivery_green.* |
| Nieuwe transport/PIT/economics counterexamples | Rode evidence, apart van fixturefout | canonical_falsification_red.*, canonical_new_counterexamples.* |
| Herstelde falsificatie plus guards | 25 pass | canonical_falsification_green.* |
| Scoped receipt/herstartcontracts | 27 pass | canonical_static_contract_reconciled.* |
| **Definitieve brede canonical suite** | **474 pass / 2 fail** | **canonical_final_regression.*** |

Exacte commands, timestamps, interpreter, cwd, environment en exitstatus staan in JSON naast de logs. De definitieve run gebruikt de echte repositorybron, niet proposed/. Er is geen steekproefresultaat tot globale E2E-PASS gepromoveerd.

## 6. Runtime-evidence

Een echte lokale subprocess-timeout test partiële niet-UTF8 stdout/stderr, exit124, RESULT-hashes en terminale FAILED-locatie. Policy-afwijzing verlaat RUNNING. De echte Bridge-handler wordt socketloos aangeroepen: eerste en herhaalde ACK blijven idempotent, outbox verdwijnt en sent blijft bestaan. Dit is handler/persistence-integratie, geen TCP/browserbewijs.

Systemd-userbus blijft Operation not permitted; lokale socketaanmaak geeft PermissionError. Laatste getraceerde scheduled-cycle receipt blijft 24 september 14:04 UTC; checkpoint was FAIL_CLOSED. Nieuwe canonical bron verandert die historical/runtimefeiten niet. Geen live hourly of browsercanary uitgevoerd. `canonical/runtime_and_git_blockers.json` bevat de actuele grenscontroles. De na herstel gelezen prod-runtime-sync receipt is nog **BLOCKED op 25 september 09:00:18 UTC**; de scheduled-cycle receipt is onveranderd. Zie `canonical/runtime_receipts_after_repair.json` (gelezen 09:38 UTC).

## 7. Alle bevindingen naar severity/status

| ID | Ernst | Actuele status | Kern |
|---|---|---|---|
| AUD-CODEX-001 | HIGH | BLOCKED | Baseline 80a5ff7 door eigenaar gecommit; vervolgauditcommits en gedeelde coordinator nog steeds geblokkeerd door read-only .git. |
| AUD-CODEX-002 | HIGH | CONFIRMED_OPEN | Actuele runtime-sync is geblokkeerd door bestaande staged wijzigingen; laatste wrapperreceipt is verouderd. |
| AUD-CODEX-003 | HIGH | FIXED_AND_RETESTED | Beide weatherrecorders gebruiken request-start als retrieved_at; KWI deelt één eerdere tijd over drie seriële fetches. |
| AUD-CODEX-004 | HIGH | FIXED_AND_RETESTED | Proof-gate accepteert negatieve, nul en niet-numerieke netto-edge plus null kostenvelden. |
| AUD-CODEX-005 | HIGH | FIXED_AND_RETESTED | Corrupt bestaande route wordt als geslaagde nieuwe route geretourneerd zonder duurzame route te schrijven. |
| AUD-CODEX-006 | MEDIUM | FIXED_AND_RETESTED | Geldige JSON met niet-objecttopniveau laat handler crashen zonder HTTP-foutresponse. |
| AUD-CODEX-007 | MEDIUM | RESIDUAL_RISK | Repositorybrede tests zijn niet groen; meerdere tests volgen oude interfaces/versies. |
| AUD-CODEX-008 | HIGH | UNPROVEN | Gevonden weatherlane bewijst geen 1–4 uur probabilistische voorspelling van definitieve TWC-settlement. |
| AUD-CODEX-009 | HIGH | FIXED_AND_RETESTED | Canonical userscript overschrijft bestaand onverzonden gebruikersconcept bij bridgelevering. |
| AUD-CODEX-010 | HIGH | FIXED_AND_RETESTED | Timeout met partiële bytes-output faalt tijdens timeoutafhandeling en verliest normaal RESULT-contract. |
| AUD-CODEX-011 | HIGH | FIXED_AND_RETESTED | Interne websocket-meetgaten en ontbrekende executable prijzen worden als bewezen geen reactie geclassificeerd. |
| AUD-CODEX-012 | HIGH | FIXED_AND_RETESTED | Prospectieve evaluator accepteert target dat al voor voorspelling compleet was, ook bij andere config. |
| AUD-CODEX-013 | MEDIUM | RESIDUAL_RISK | Geinstalleerde componenten gebruiken verschillende repositories en userscript wijkt af van canonical Git-bestand. |
| AUD-CODEX-014 | LOW | RESIDUAL_RISK | 14 van 726 Pythonbestanden hebben syntaxfouten; historische mislukte jobs mogen niet als opnieuw uitvoerbaar worden behandeld. |
| AUD-CODEX-015 | HIGH | FIXED_AND_RETESTED | Productie-executor importeert ontbrekende policy_check-module. |
| AUD-CODEX-016 | MEDIUM | FIXED_AND_RETESTED | Malformed HTTP200 van upstream wordt als succes doorgegeven. |
| AUD-CODEX-017 | MEDIUM | FIXED_AND_RETESTED | Eerste draftbehoudpatch strandde eigen invoer na ontbrekende sendknop. |
| AUD-CODEX-018 | HIGH | FIXED_AND_RETESTED | Policy-afgewezen taak blijft in RUNNING-directory achter. |
| AUD-CODEX-019 | HIGH | FIXED_AND_RETESTED | Leeg invoerveld wordt zonder nieuwe userturn als geslaagde levering behandeld. |
| AUD-CODEX-020 | HIGH | FIXED_AND_RETESTED | Foreign ticker en niet-eindige post-event prijs worden als reactie gescoord. |
| AUD-CODEX-021 | MEDIUM | FIXED_AND_RETESTED | Raw TimeoutError/OSError uit upstream ontsnapt aan expliciete foutrespons. |
| AUD-CODEX-022 | HIGH | FIXED_AND_RETESTED | Batchvolgorde overschrijft echte vroegste city-receipt niet. |
| AUD-CODEX-023 | HIGH | FIXED_AND_RETESTED | Canonical wake loop mist task/payload-dedupe, retrybackoff en userturn-recovery. |

## 8. Canonical gerepareerde bevindingen

003: request-start en response-body receipt gescheiden, per-city receipt en expliciete provenance.
004: ontbrekende/negatieve/nul/niet-eindige economics fail-closed; ook zeer grote JSON-integers veroorzaken geen OverflowError meer.
005/006/016/021: corrupt routebestand niet als succes, begrensde object-envelopevalidatie, expliciet upstreamsuccesscontract en zichtbare transportfoutrespons.
009/017/019/023: conceptbehoud, eigenaarschap bij retry, zichtbare userturnbevestiging, volledige chat/task/payload-scoping, durable receipts vóór ACK en 60s retrybackoff. Userscriptmetadata v0.4.7. Gewijzigde payload voor dezelfde task wordt niet stil weggefilterd; partial anchor is geen leveringsbewijs.
010/015/018: timeoutbytes veilig decoderen, foutlifecycle, ontbrekende research-only policydependency hersteld met fail-closed configcheck en terminale policyqueue.
011/012/020/022: coveragegaten/ongeldige executable baseline → UNPROVEN, strikt later target met gelijke config, ongeldige/foreign post-state afgewezen en selectie op werkelijk vroegste cityreceipt onafhankelijk van batchvolgorde.

Alle genoemde bronwijzigingen bestaan canonical en relevante tests slagen. `remediation_commit` blijft null zolang Git niet kan schrijven; dat wordt niet verborgen. Bron-FIXED_AND_RETESTED is geen attestatie van deployed processen.

## 9. Resterende failures en bevindingen

**Sockettest:** daadwerkelijke TCP-test kan geen socket maken binnen deze sandbox. Bestaande test intact en rood; nieuwe socketloze handler/persistencetest groen. Geen E2E-PASS.

**Installerpolicy:** oude test eist 15s fast-deadman; bestaande staged eigenaarinstaller bewaart expliciet 600s inactivity. Beide intenties zijn bewaard. Geen interval gewijzigd en geen 15s-assertion versoepeld. Nieuwe gedragstest bevestigt bij de ownerbron 600s, idempotente patchgeneratie, unieke retry-nonce en fresh-task-ID-instructie. De operationeel gewenste SLA is daarmee nog niet beslist.

De drie tijdelijk bijkomende failures in canonical_final_full waren oude @version0.3.3- en raw-event-id-bronpatronen. Versiecontract is naar de werkelijke v0.4.7 gebracht; dedupechecks voeren nu werkelijk herstel na nieuwe scriptinstantie en storage-before-ACK uit. Negatieve evidence blijft bewaard.

## 10. BLOCKED / UNPROVEN

Lokale canonical commits/coordinator binnen deze toolomgeving; echte systemd/TCP/browser/rebootcanary; actuele hourly-completion; volledige externe modelinvocatietrace; legacy-checkout deployment; finale TWC-doelvalidatie, holdouttoegangsverleden en executionbewijs. Geen ontbrekend bewijs als PASS geclassificeerd.

## 11. Residuele risico's

Onbekende historische receiptkwaliteit blijft onbekend; oude data worden niet herschreven. De lexicale policychecker is geen volledige command-sandbox. Node-tests modelleren DOM en storage, maar bewijzen geen echte browservirtualisatie/timing of alle meervoudige tabs. Scoped cache gebruikt andere keys dan oude globals; deployment/migratie vereist expliciete canary. Full crash/reboot recovery en alle concurrencygevallen zijn niet bewezen. Oude historische failurejobs blijven bewaard.

## 12. Weather/TWC wetenschappelijke conclusie

**UNPROVEN** voor probabilistisch voorspellen van finale TWC settlement 1–4 uur vooruit. KWI-minute publication-lag is een ander target. Geen interne TWC-werking aangenomen zonder primaire evidence. Receipt-reparaties maken gegevens niet retrospectief point-in-time.

Persistence is aangetroffen; vergelijkbare OOS trend/METAR-ASOS/NWP/gecombineerde Weather Runner-baselines en volledige CRPS/Brier/logloss/calibration/reliability/sharpness-kwalificatie zijn niet aangetoond. Geen nieuwe strategie ontwikkeld om historische resultaten te verbeteren.

## 13. Point-in-time conclusie

De bevestigde lokale receipt-/chronology-/configdefecten zijn canonical gerepareerd en synthetisch gefalsificeerd/hergetest. Nieuwe test bewijst dat de vroegste cityreceipt prevaleert boven de aggregate batchvolgorde. Legacy manifests zonder expliciete receiptsemantiek worden uitgesloten. Dit kan eerdere eligible aantallen laten verdwijnen: fail-closed, geen negatief signaalbewijs op zichzelf.

Volledige PIT-validiteit over alle forecastavailability/revisie/feature/settlementpaden blijft UNPROVEN. Geen herlabeling of achteraf verzonnen timestamps.

## 14. Holdoutintegriteit

**UNPROVEN.** Geen afdoende untouched holdout/toegangsgeschiedenis aangetoond. Station×local_date-afhankelijkheid en gedeelde settlementbuckets blijven relevant; eventcounts zijn geen onafhankelijke trials. Geen tuning of hergebruik als nieuwe holdout.

## 15. Signal-edge status

**NO_PROVEN_EDGE / UNPROVEN** voor het gevraagde finale TWC-target. Technische gates en mechanismeobservaties zijn geen economische edge. Geen performance, significantie of P&L verzonnen.

## 16. Market-edge status

**NO_PROVEN_EDGE.** Geen volledige combinatie van point-in-time executable bid/ask, L2 quantity, fees, slippage, fills, retail-latency, collateral en settlementfinality. Geen geobserveerde reactie betekent niet dat informatie nog buiten prijzen ligt. Geen orders of testorders uitgevoerd.

## 17. Prediction Bridge-conclusie

Afgebakende canonical fouten gerepareerd; routing/envelope/transport, ACKpersistency en browserdeliverygedrag hebben negatieve én positieve tests. Actual loaded browser/runtime niet geattesteerd. Geen algemene Bridge-E2E-PASS.

## 18. Agents/orchestratie-conclusie

Historische vijf responsebundels met zes rollen zijn getraceerd naar packets/receipts/downstream. Canonical proof-gate en relevante orchestratiesuites slagen. Actuele volledige hourly-keten blijft niet aangetoond en eerder geblokkeerd door userindex/sync. Deze guard niet omzeild; queue niet hervat.

## 19. Definitieve regressie

476 canonical tests verzameld: 474 pass, 2 expliciet geclassificeerde fail. Geen verborgen xfail/skip om de twee failures te maskeren. 64 oorspronkelijke auditchecks plus aanvullende falsificaties zijn opgenomen. Groene positieve controls voorkomen dat alles eenvoudigweg geweigerd wordt.

## 20. Nieuwe adversariële review van gerepareerde bron

Nieuwe rode counterexamples: dubbele delivery/ACKretry/recovery/backoff; raw upstream timeout; zeer groot integer in finite-economicscheck; vroegste cityreceipt verstopt in later manifest. Alle kregen minimale reparatie en groene focused plus brede canonical regressie. Een onjuist gemockte handlerreplynaam was een auditfixturefout en is zo geclassificeerd, geen productiebug.

Review is door dezelfde auditor met nieuwe failure modes uitgevoerd; geen tweede persoon/model gefingeerd.

## 21. Finale falsificatie en drievoudige zelfcontrole

Semantiek/provenance: sourcebasis, per-city receipt, config/targetidentiteit en ownerpolicy gecontroleerd. Data/reproduceerbaarheid: bewaarde red/green counterexamples, volledige canonical suite en exacte codehashes. Economie/execution: geen volledig bewijs; daarom geen promotie.

PIT-, proof-, terminalisatie-, timeout-, route-, malformed-response-, draft-, false-delivery-, coverage- en chronologyclaims zijn op hun begrensde gedrag getest. Grote claims blijven verworpen/onbewezen: huidige hourly werkt, alle processen gebruiken gerepareerde bron, browser-E2E werkt, holdout intact, signal/market edge bewezen. Een actief proces of groen unittestresultaat vervangt die evidence niet.

## 22. CONTINUATION / aanbevelingen

1. Maak de zes afgebakende lokale commits volgens `canonical/COMMIT_PLAN.md`. Het geteste script bewaart overige staged ownerbestanden. Routercommit omvat expliciet de vooraf staged consumer-routingbasis plus reparatie; geen blind opnieuw toepassen van de patch.
2. Binnen normale toegestane runtimecontext: beslis het 15s/600s-SLAconflict, test de ongewijzigde sockettest, attesteer werkelijk geladen code en voer een read-only/shadow browser/hourly-canary uit. Geen handels-, wallet- of betaalde activatie.
3. Reconcile legacy weathercheckout en canonical repair via gecontroleerde deployment; registreer eventuele meetgaten. Niet aannemen dat wijziging in prod de legacy recorder heeft bijgewerkt.
4. Pas na echte runtime/recovery-evidence en passende wetenschappelijke gates herkwalificeren. Geen holdout relabeling, geen edgepromotie uit technische PASS.

Geen verdere reset geactiveerd. De resterende grenscontroles vereisen een andere feitelijk toegankelijke runtime/Git-context of inhoudelijke SLAkeuze; ze zijn niet opgelost door ruimere rechten te vragen.

## 23. Exacte evidence/commitreferenties

80a5ff7: baseline. db6c0f3: gecommitte eerdere audit/proposals. Geen volgende canonical commit beschikbaar binnen sandbox.

`canonical/preflight.json`, `integration.jsonl`, `canonical_change_manifest.json`, `canonical_changes.patch` en `before/` koppelen bronbasis aan reparaties zonder userwerkverlies. `remediation/canonical_*.json/.log` bevatten reproduceerbare tests. `canonical/runtime_and_git_blockers.json` onderbouwt grenzen. `canonical/commit_plan_test.json` bewijst alleen veilige commitselectie in een eigen lokale testrepo. FINDINGS.jsonl is het actuele permanente register; eerdere rapportversies/evidence blijven in Git beschikbaar.
