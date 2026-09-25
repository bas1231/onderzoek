# Onafhankelijke kwalificatie — 25 september 2026

## 1. Eindstatus

**AUDIT_FAIL + AUDIT_INCOMPLETE + NO_PROVEN_EDGE.**

De geteste implementatie bevat reproduceerbare HIGH correctnessfouten. End-to-end betrouwbaarheid en wetenschappelijke geldigheid zijn niet aangetoond. AUDIT_PASS_WITH_TESTED_ASSURANCE is niet toegestaan. Geen uitspraak dat de repository overal defect is: veel begrensde controles slagen.

## 2. Kernuitkomst

- Bestaande suite: **374 passed, 17 failed** in geïsoleerde kopie met eigen Git-testmetadata. Eén failure is een sandbox-geblokkeerde sockettest; andere failures omvatten stale interfaces, fixturetekorten en echte verschillen in safeguards.
- Negen nieuwe negatieve gedragstests: **9 failed**, herhaald. Ze toetsen de gewenste invarianten en bevestigen defecten; geen assertions versoepeld.
- Weatherontvangst wordt vóór feitelijke responseontvangst gedateerd. Het markt-reactiepad kan meetgaten en lege executable boeken als bewijs van geen reactie behandelen. Een prospectieve evaluator accepteert een al eerder bekend target.
- Proof-gate accepteert negatieve/nul/niet-numerieke netto-edge. Bridge-routecorruptie, JSON-typeafhandeling, conceptverlies en executor-timeout zijn gereproduceerd.
- Productiereparaties en alle canonical auditcommits zijn **BLOCKED**: `.git` is read-only en baselinecommit is verplicht vóór reparatie. Er zijn geen ruimere rechten gevraagd en geen productiecodewijzigingen gedaan.

## 3. Exacte scope en baseline

Repository `/home/leonh/prediction_research_prod`, HEAD `6b33058` (volledig SHA in baseline_head.json), huidige werkboom inclusief vooraf staged/unstaged wijzigingen. 3.469 getrackte bestanden gehasht; 78 testbestanden geïnventariseerd in tests/, control/weather en control/tampermonkey_multichat. Eén root AGENTS.md gevonden, geen nested instructies bij hidden-file scan. Methodologie, negative ledger, lokale uitvoeringsregels en parallel/build-governance gelezen.

Read-only onderzoek omvat actuele canonical source, relevante Git-historie, lokaal geïnstalleerde units/scripts, lokale state/receipts, weatherraw/manifests en historische bridgefouten. Productie-services, browser-DOM en externe modelinvocaties zijn niet live getest. Eénmalige research-/deploymentjobs zijn niet ongericht uitgevoerd. Geen volledige audit van alle andere private bronrepo's of alle historische Git-blobs.

Pre-existing userwerk bleef onaangeraakt: controle van alle baselinehashes vond **nul gewijzigde getrackte bestanden**. Alleen knowledge/codex_audit is geschreven. Index/HEAD zijn niet gewijzigd; geen stash/reset/clean/rebase/push. Tijdelijke lokale test-Git-repositories zijn geen canonical auditledger.

## 4. Werkelijk geobserveerde architectuur

Zie SYSTEM_MAP.md. Hourly timer → runtime_sync → edge_hunter_cycle → hourly_cycle/bronverwerking/packets/recon/queue → AI bundle/exchange → responsevalidator → packets/receipt/orchestration → checkpoint. ChatGPT vervult Directorrol; registry v4 bevat zes permanente domeinrollen plus tijdelijke independent_reproducer. Dit is geen bewijs van zeven of zes onafhankelijke LLM-processen.

Multi-chat bridge en legacy researchbridge zijn afzonderlijke paden. Weathercollectors/E401/lifecycle units gebruiken nog de afzonderlijke legacy checkout, hourly/executor prod. Vier kern-weatherbestanden in die checkout matchen prod byte-voor-byte bij deze audit. Geïnstalleerde userscriptversie verschilt van canonical bron; browsergeladen versie onbekend.

## 5. Tests uitgevoerd

| Controle | Resultaat | Evidence |
|---|---|---|
| Eerste geïsoleerde suite zonder Gitmetadata | 363 passed / 28 failed | baseline_pytest.* |
| Zelfde bron, lege lokale Git-testcommit toegevoegd | 374 passed / 17 failed | baseline_pytest_git_fixture.* |
| Receiptklok met synthetische netwerkvertraging | 5/10/15 seconden terugdatering KWI; 5 seconden TWC | final_reproductions.log |
| Proof-gate met -1, 0 en unknown netto-edge | Alle geaccepteerd | final_reproductions.log |
| Corrupte route, JSON-array | False success respectievelijk AttributeError | final_reproductions.log |
| Executor timeout met partiële bytes | TypeError; normaal RESULT ontbreekt | final_reproductions.log |
| Werkelijke Python subprocess-timeout | stdout/stderr bytes ondanks text=True | real_timeout_type.json |
| Coveragegat/lege bid-ask | Beide onterecht NO_REACTION | final_reproductions.log |
| Target eerder bekend/cross-config | Row wordt gescoord, lead -10 seconden | final_reproductions.log |
| Userscript submitMessage in Node-fixture | Concept overschreven, bridgebericht verstuurd | final_composer.log |
| Negatieve regressietests | 9 failed, tweemaal | final_adversarial.log |
| Raw-hashsteekproef | 20/20 match | provenance_tests_security.json |

Opdrachten, interpreter, timestamps en exitcodes staan in test_runs/*meta.json en baseline*.json. Synthetische values zijn nadrukkelijk geen marktprijzen, fills of empirische netwerklatenties.

## 6. Runtime-evidence

Laatste gelezen prod-runtime-sync: **BLOCKED**, 2026-09-25 06:23 UTC, bestaande staged index. Laatste scheduled-cycle receipt: 2026-09-24 14:04 UTC, run hourly-20260924T160000+0200. Git-checkpoint van 15:13 UTC: FAIL_CLOSED, HEAD verschilt van origin/main. Deze receipts ondersteunen geen huidige hourly-PASS.

Weatherbestanden worden wel recent aangemaakt: inventaris bevatte 6.425 KWI-manifests, 438 TWC-manifests, 9.912 E401 manifestbestanden en 4.626 market logs. Bestandsaantallen bewijzen geen valide onderzoek. Twee E401-analyserapporten dateren van 21 september; het ene rapporteert slechts 13/68 evalueerbare events (0,191 synchronized fraction). Actuele fresh analysis/consumptie is niet aangetoond.

Systemd-userbus geeft Operation not permitted. Geen actieve-serviceclaim op basis van diskconfig of receipts. Geen live HTTP/DOM-roundtrip, reboot of recoveryrestart uitgevoerd.

## 7. Bevindingen naar severity

Zie FINDINGS.jsonl voor permanente schema's, verwachte/waargenomen werking, reproducties en herstelvoorstellen.

| ID | Severity/status | Kern |
|---|---|---|
| 001 | HIGH / BLOCKED | Git-ledger/baselinecommit en coordinator niet schrijfbaar |
| 002 | HIGH / CONFIRMED | Actuele hourly-preflight geblokkeerd; receipt stale |
| 003 | HIGH / CONFIRMED | Weatherreceipt vóór responseontvangst |
| 004 | HIGH / CONFIRMED | Proof-gate accepteert ongeldige economics |
| 005 | HIGH / CONFIRMED | Corrupt routebestand geeft onterecht geslaagde route |
| 006 | MEDIUM / CONFIRMED | JSON-array veroorzaakt onbehandelde handlerexception |
| 007 | MEDIUM / CONFIRMED | Suite/contract/testdrift en ontbrekende negatieve dekking |
| 008 | HIGH / UNPROVEN | Gevraagde 1–4 uur final-TWC voorspelarchitectuur niet bewezen |
| 009 | HIGH / CONFIRMED | Canonical userscript overschrijft onverzonden concept |
| 010 | HIGH / CONFIRMED | Timeoutafhandeling breekt normaal RESULT/lifecyclecontract |
| 011 | HIGH / CONFIRMED | Meetgat/lege executable state geven onterechte no-reaction |
| 012 | HIGH / CONFIRMED | Evaluator accepteert niet-prospectief/cross-config target |
| 013 | MEDIUM / RESIDUAL_RISK | Deployment/bronversies verschillen |

Prefix voor alle IDs: AUD-CODEX-. Geen CRITICAL vastgesteld; dit is geen uitsluiting van nog onbekende criticals.

## 8. Gerepareerde bevindingen

**Geen.** Baselinecommit is hard geblokkeerd, dus productieherstel mag volgens de opdracht niet starten. Geen FIXED-status op basis van alleen een patch. Alle oorspronkelijke negatieve resultaten blijven behouden.

## 9. Resterende bevindingen

Alle bovenstaande bevindingen blijven open, blocked, unproven of residual risk. Negen regressietests blijven bewust rood. Prioriteit: PIT/target/coverage, proof-gate, bridge/timeout, daarna deployment/testdrift en real-runtime canary.

## 10. Geblokkeerde/onbewezen gebieden

Canonical commit; eigen worktree/lease; productieherstel; live systemd/HTTP/DOM; daadwerkelijk reboot-/crashherstel; externe AI-invocatietraces; volledige private Weather Runner; signal/market/holdoutvalidatie; alle benodigde fees/L2/fill/latency/finalitybewijzen.

## 11. Residual risks

Zie RESIDUAL_RISKS.md. Kern: goede hashes bewijzen geen beschikbaarheidstijd; goede JSON-ontvangst bewijst geen onafhankelijk wetenschappelijk oordeel; lokale tests bewijzen geen browser/deploymentwerking. Onbekende bronrevision/finality/DST-gevolgen blijven onbekend.

## 12. Weather/TWC wetenschappelijke conclusie

Gevonden evidence gaat hoofdzakelijk over **publicatie-/completionlag in KWI-minuutdata**, plus TWC-weekobservatierecording. Dit is een ander target/horizon dan een probabilistische voorspelling van de definitieve TWC-hourly settlement 1–4 uur vooruit. Settlement-equivalentie tussen deze lanes is niet bewezen en wordt niet aangenomen.

De eenvoudige incomplete-stationmean was al REJECTED_IN_DEVELOPMENT: gerapporteerde MAE 0,20417 versus persistence 0,08481 bij 459 paren. Dit is bestaande repo-evidence, niet opnieuw berekende onafhankelijke performance. De full-stationvariant is expliciet post-hoc ontdekt en prospectief geregistreerd; dat maakt vooraf bekeken data niet untouched. Bestaande negatieve conclusies zijn behouden.

Baselines: persistence gevonden; trend, aparte METAR/ASOS-nowcast, short-horizon NWP en gecombineerde Weather Runner zijn niet als vergelijkbare OOS-evaluatie aangetoond in de getraceerde lane. MAE/RMSE worden berekend; CRPS/Brier/logloss/calibration/reliability/sharpness niet als voldoende gevalideerde suite aangetoond. Geen ensemblecounting of AUC-promotie gebruikt.

## 13. Point-in-time conclusie

**FAIL voor de geteste garanties.** Request-start wordt als ontvangsttijd gebruikt en E401 vertrouwt daarop. Synthetische controle toont te vroege beschikbaarheid. De evaluator sluit targets die eerder compleet waren niet uit. Configidentiteit wordt onvoldoende afgedwongen. Dit bewijst een codepadfout, niet dat iedere historische row gelekt is.

Aanvullende check van opgeslagen E369-checkpoints vond in de onderzochte rows geen niet-positieve lead (zie second_pass_historical_check.json); dat falsificeert de codefout niet en voorkomt de overdreven claim dat historische contaminatie al is aangetoond. Repareer historische tijden niet met verzonnen receipt-end.

## 14. Holdout-integriteit

**UNPROVEN.** Geen complete toegangsgeschiedenis of afgeschermde untouched holdout voor het gevraagde target aangetoond. Protocol verlangt temporal split pas na feasibility; bestaande checks zijn development/prospective mechanism gates, geen universele holdoutbevestiging. Geen data geherlabeld, geen model geoptimaliseerd, geen parameters afgestemd.

E401 telt city×target-minute primaries en scheidt revisies; buckets worden samen bekeken. Minuten binnen dezelfde city/local-date blijven gecorreleerd. Drempels op eventcount zijn geen bewijs van onafhankelijke statistische trials. Audit heeft geen p-waarden of signal-P&L gecreëerd.

## 15. Signal-edge status

**UNPROVEN voor 1–4 uur final-TWC.** Bestaande KWI signal-observaties mogen niet tot dit target worden opgewaardeerd. De nulconclusie NO_PROVEN_EDGE is gehandhaafd.

## 16. Market/execution-edge status

**NO_PROVEN_EDGE.** Reactietiming is geen causale winst of fill. Zonder valide PIT, contract/ruleversie, gelijktijdige executable quotes/depth, fees, latency/queue/fill/partial-fill, collateral en finality kan geen conservatieve positieve nettocashflow worden vastgesteld. Geen orders, wallets, live-P&L of betaalde diensten gebruikt.

De positieve proof_gate-uitkomst bij negatieve economics is een softwarefout, geen edge. PROVEN_EDGE_CANDIDATE is bovendien een candidate-label, niet daadwerkelijke live-validatie. Er is geen historische onterechte promotie aangetoond.

## 17. Bridge-betrouwbaarheid

**FAIL voor de gereproduceerde broncodegaranties; runtime-E2E UNPROVEN.** Routecorruptie, JSON-topniveau en conceptverlies zijn bevestigd. Historische E402R2/E403/E404 stderr en RESULT-artifacts bevestigen NameError/SyntaxError-klassen; hun source/deliverytransformatie is niet opnieuw via browser gereproduceerd. Geen bridge als bewijs van zichzelf vertrouwd.

Bestaande tests dekken verschillende ACK/replay/transport/preflight/recoverygevallen, maar één sockettest is sandbox-blocked. Malformed/truncated/large framing is niet integraal door een echte browserketen gegaan. Installed router matcht huidige staged bron; installed userscript verschilt, dus canonical JS-defect wordt niet als bewezen huidige browserincident gepresenteerd.

## 18. Agents/orchestration

Vijf historische responses op 24 september bevatten elk zes roles met bundle, receipt en downstream packet/applied_at. Dit weerlegt de algemene hypothese “geen role-output wordt geconsumeerd”. Het bewijst geen zes onafhankelijke agentinvocaties of inhoudelijke voltooiing: market_research en algebra staan in relevante samples nog WAITING_FOR_RESULT/DATA.

Independent_reproducer heeft geen volledig echt survivaltraject in deze audit. Deterministische tests geven beperkte contractzekerheid. Hourly is momenteel niet gekwalificeerd door blocked sync en stale receipt; automatische collectors zijn een aparte keten.

## 19. Regressieresultaten en testkwaliteit

Volledige veilige suite van de drie genoemde testlocaties gedraaid. Elf eerste failures verdwenen met uitsluitend Gitmetadata in de fixture: geen productiedefecten. Warrant-test faalt door ontbrekende autonomous-build-policy in zijn tijdelijke root (`autonomous_build_policy_error:FileNotFoundError`). Registrytest verwacht v3 terwijl huidige v4 aanwezig is. Vijf WS-tests gebruiken een oude handle_message-signatuur. Per-ticker sequence-gaptest weerspreekt de actuele subscription-scoped sequencing; **geen bevestigd ontbrekend sequence-veto**. De interleaved subscription-test doorloopt de actuele tracker.

Static userscripttests vormen geen DOM-E2E; de Node-gedragstest levert het specifieke drafttegenvoorbeeld. Geen volledige productieregressie-na-reparatie mogelijk omdat er geen reparatie is gedaan. De finale negen rode auditregressies bevestigen dezelfde gewenste invarianten, zonder testweakening.

## 20. Tweede adversariële review

Nieuwe failure modes gezocht buiten de eerste fouten: partial-output timeout, interne coveragegaten, lege boeken, targetvolgorde/config en installed-source provenance. Nieuwe bevindingen 010–013. Review door dezelfde auditor met nieuwe tegenvoorbeelden; **geen onafhankelijk tweede reviewer/model**. Remediationreview niet uitgevoerd wegens commitblokkade.

## 21. Finale falsificatie en zelfcontrole

- “PIT klopt”: weerlegd door fake-clock/responsebewijs en bron→consumertrace.
- “Proof-gate vereist positieve economics”: weerlegd met drie ongeldige waarden.
- “No reaction impliceert volledige executable coverage”: weerlegd door gat/lege state.
- “Alle targets zijn later bekend”: weerlegd met negatieve lead; historische occurrence niet aangetoond.
- “Bridge bewaart gebruikersconcept”: weerlegd in ongewijzigde submitMessage.
- “Timeout resulteert altijd in normaal failure-artifact”: weerlegd met bytes en echte subprocess-typecheck.
- “Iedere agent produceert nooit output”: verworpen door historische packets/receipts.
- “Hourly werkt nu”: niet te bewijzen; laatste preflight is blocked.
- “Ruwe evidence is hash-consistent”: steekproef ondersteunt dit, geen claim voor volledige corpusintegriteit.

Per belangrijke bevinding: bron/semantiek, reproductie/data en economische/execution-implicatie beoordeeld. Niet beschikbare onafhankelijke dataset/implementatie, echte fills en browser/runtimeverificatie expliciet niet ingevuld. Geen van deze beperkingen als PASS behandeld.

## 22. Vervolg en stop-check

Veilige auditpasses en tegenvoorbeelden zijn opgeslagen; noodzakelijke volgende stappen zijn blocked: baselinecommit/lease, productieherstel en echte runtimechecks. De auditor verandert de sandbox niet. Niet stoppen wegens één mislukte test: onafhankelijke code-, data-, historische en failure-injectionpasses zijn voortgezet. Geen queueherstart, geldactie of nieuwe experimentservice nodig/uitgevoerd.

### CONTINUATION

1. Lees dit rapport, OPEN_FINDINGS en hashes; controleer opnieuw bestaand userwerk.
2. Leg **uitsluitend** knowledge/codex_audit lokaal vast; behoud overige staged inhoud. Geen push. De commando's hieronder draaien in een subshell; de interactieve terminal blijft open.
3. Verifieer commitinhoud, start daarna volgens projectregels een eigen reparatieworktree/lease en frozen charter. Werk findings één voor één af met oorspronkelijke rode test → fix → subsystemen → brede regressie → onafhankelijke runtimecanary.
4. Prioriteit AUD-003/011/012, dan AUD-004 en bridge/timeout. Verzamel nieuwe correcte prospectieve data; geen oude timestamps/holdout “repareren” door relabeling.
5. Userwerk op main eerst expliciet reconciliëren; geen reset/clean/stash over bestaande wijzigingen. Geen services blind restarten.

```bash
(
  cd /home/leonh/prediction_research_prod &&
  git status --short &&
  git add -- knowledge/codex_audit &&
  git commit --only -m 'audit: record independent qualification and blockers' -- knowledge/codex_audit &&
  git show --stat --oneline HEAD
) || printf '%s\n' 'STOP: auditcommit niet afgerond; bestaande wijzigingen behouden, terminal blijft open.'
```

## 23. Evidence en commitreferenties

- Baseline HEAD/branches/status/worktrees/history: evidence/baseline_*.json.
- Bronbestanden: evidence/baseline_manifest.json; behoudcontrole: evidence/preservation_check.json.
- Runtime/rollen: evidence/runtime_and_agent_trace.json; deployment: installed_configuration.json.
- Raw/secret/testinventaris: provenance_tests_security.json; aanvullende historische controle: second_pass_historical_check.json.
- Historische bridgefailures: historical_bridge_errors.json en oorspronkelijke control/results-artifacts.
- Reproductiebron: evidence/reproduce_defects.py, composer_reproduction.js, test_audit_regressions.py.
- Exacte finale opdrachten/resultaten: test_runs/final_* en baseline_pytest_git_fixture.*.
- Oorspronkelijke KWI-recordercommit `e2cfb82`; canonical userscript laatste genoemde commit `7d583e2`; executor provenancewijziging `d0dac22`.
- **Audit-/remediationcommits: GEEN, BLOCKED.** Er is niets gepusht. Workspace-evidence is aanwezig maar de gevraagde Git-ledgerplicht is niet voltooid.

## Aanvullende finale breedtecontrole

726 Pythonbestanden geparseerd zonder uitvoering: 14 syntaxfouten, geregistreerd als AUD-CODEX-014 (LOW / RESIDUAL_RISK) en naar historische tasks gemapt. Geen aanleiding om negatieve historische artefacten te wissen. Alle 6 JavaScriptbestanden passeren node --check; dit bewijst geen browsergedrag.

454 RESULT.json-bestanden geparseerd en 904 stdout/stderr-hashes opnieuw berekend: nul parsefouten, ontbrekende logbestanden of hashmismatches. Dit ondersteunt historische logintegriteit, niet de inhoudelijke juistheid van PASS-markers. Evidence: broad_static_history_check.json en syntax_failure_task_mapping.json. Totale bevindingen: 14.
