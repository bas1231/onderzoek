> FINAL QUALIFICATION: zes repaircommits en 22 repairhashes bevestigd; 475 pass / 1 socketbeperking. Default 600s-bronbeleid vastgesteld; ownerinstaller/index intact. Runtime wacht op externe WSL-evidence. Zie canonical/WSL_QUALIFICATION.md en FINAL_AUDIT_REPORT.md voor actuele kwalificatie. Oudere checkpointtekst hieronder is historisch.

# Testmatrix

| Test | Resultaat | Beperking |
|---|---|---|
| Baseline geïsoleerde werkboom | 363 passed / 28 failed | 11 failures door ontbrekende Git-testmetadata |
| Git-testfixture toegevoegd, zelfde bron | 374 passed / 17 failed | 1 sockettest sandbox-blocked; overige failures onderzocht |
| Recorder fake klok + vertraagde response | Terugdatering bevestigd | Geen echte netwerklatency gemeten |
| Proof gate negatieve/ongeldige economics | Onterecht geaccepteerd | Geen historische promotie geclaimd |
| Corrupte route + JSON-array | False success / handlerexception | Geen live bridge |
| Composer Node-harness | Draftverlies bevestigd | Geen browser-DOMtest |
| Executor timeout met bytes | TypeError, RESULT ontbreekt | Outer errorpad apart gelezen |
| Raw-hashsteekproef | 20/20 gelijk | Geen bewijs van receipt-tijd/finality |
| Historische agents | 5 responses × 6 rollen met packets/receipts | Geen bewijs onafhankelijke modelinvocaties |

Exacte opdrachten, timestamps en exitcodes: test_runs/. Eerste audit-harnesspogingen hadden importpad/Path-namespacefouten; alleen testharness hersteld, geen productiecode.

## Finale negatieve checks

Negen gewenste invarianten blijven rood: final_adversarial.log (9 failed). final_reproductions_meta.json en final_composer_meta.json bevatten exacte opdrachten/tijden/exitcodes. De helpers eindigen met rc=0 omdat zij waarnemingen rapporteren; dat is geen systeem-PASS.

Warrantfailure afzonderlijk geclassificeerd als ontbrekende policyfixture; zie warrant_failure_classification.json. Tweede review: coveragegat/lege quote en target vooraf bekend; zie final_reproductions.log. Geen productieregressie-na-fix: er was geen toegestane fix.

Brede read-only controle: 726 Python AST-parses (14 historische syntaxfouten); 6 JS syntaxchecks geslaagd; 454 RESULT-objecten en 904 loghashes zonder mismatch. Zie evidence/broad_static_history_check.json.

## Hervatting na baseline 80a5ff7

Baseline door eigenaar veilig gecommit en geverifieerd. Vervolgcommits/coordinator blijven read-only. Productiebronhashes ongewijzigd. Voorstellen, exacte commands en resultaten: `remediation/`. Nieuwe bevindingen AUD-CODEX-015 t/m 018; geen productiefix geclaimd. Nieuwe gedragstests: 52 passed. Breedste huidige regressie: 444 passed, 8 failed (broad_v3). De oorspronkelijke negen invarianten slagen in de voorstelkopie; oorspronkelijke rode evidence blijft bewaard.

## Actuele hervattingsstatus — 25 september 2026

Baseline 80a5ff7 is geverifieerd en veilig. Oudere tekst over ontbrekende baselinecommit is historisch; vervolgcommits/lease blijven geblokkeerd door read-only .git. Productie ongewijzigd. Zie FINAL_AUDIT_REPORT.md en remediation/TRIAGE.md: 20 bevindingen, 64 auditchecks geslaagd op voorstelbron; brede suite en duurzame replay beide 447 passed / 8 failed. Geen productie-FIXED/RETESTED. Frozen acceptancecriteria zijn niet versoepeld. Exact vervolg staat in CONTINUATION.

## Canonical herstel — 25 september 2026

De eerdere voorstelstatus is opgevolgd door echte canonical integratie op db6c0f3. Alle 17 bronbases matchten exact; userindex en niet-gerelateerde tracked bestanden zijn ongewijzigd. 64 oorspronkelijke auditchecks en nieuwe relevante suites slagen. Nieuwe bevindingen 021–023 gerepareerd en gericht hergetest. Eerste brede canonical run: 447/8; na extra safeguards 469/5, waarvan drie stale bronpatronen nu door gedragstests gedekt zijn. Definitieve hertest volgt. Geen production-deployment-PASS; Git blijft read-only. Zie canonical/canonical_change_manifest.json en canonical_changes.patch.

## Definitieve canonical matrix

| Scope | Bewijs | Resultaat |
|---|---|---|
| Weather/PIT | canonical_weather | 39 pass |
| Proof | canonical_proof | 16 pass |
| Bridge | canonical_bridge | 34 pass |
| Executor/policy | canonical_executor | 20 pass |
| Oorspronkelijke audit + delivery | canonical_delivery_green | 71 pass |
| Nieuwe falsificatie + guards | canonical_falsification_green | 25 pass |
| Scoped persistent deliverycontracts | canonical_static_contract_reconciled | 27 pass |
| Volledige veilige canonical scope | canonical_final_regression | 474 pass / 2 fail |
| Gitcommitselectie, aparte fixture | canonical/commit_plan_test.json | 6 lokale fixturecommits; ownerindex behouden |

Logs/metadatasets onder remediation/, altijd werkelijke cwd en exitstatus inspecteren. De definitieve suite omvat oorspronkelijke 64 auditchecks. Sockettest faalt door PermissionError; oude installer15s-check conflicteert met staged600s-ownerbeleid. Geen tests versoepeld of stil overgeslagen.

## Externe eindresultaten (werkelijk WSL, geen sandboxselftest)

| Evidence | Uitkomst | Betekenis |
|---|---|---|
| external_runs/20260925T095320Z-9b5ee7a3/offline_contracts.log |128 passed, exit0 | Bestaande canonical contracts; overlap met vorige475 |
| Zelfde map/real_loopback.log |4 passed, exit0 | Werkelijke tijdelijke HTTP/ACK/routing/rebind |
| RESULT.json/systemd_observation |exit0 | Services observeerbaar; hourly failed, niet automatisch PASS |
| RESULT.json/health |8765/8767 HTTP200 | Bereikbaar; geen code-/ketenattestatie |
| RESULT.json/deployment_file_comparison |5 verschillen;4 exact oude bekende bron | Deploymentgap, geen nieuwe canonical bug |

De oude socketfailure slaagt extern. Geen nieuwe volledige476-test-run of optelling van overlappende suites verzonnen. Globale productie-E2E blijft ongekwalificeerd wegens concrete operationele blockers.
