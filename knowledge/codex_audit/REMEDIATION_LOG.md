## Operationele aanvulling 26 september 2026

De permanente Codex user-service/timer is geïnstalleerd en enabled. Hourly gebruikt nu een eigen additive drop-in naar de geteste geïsoleerde no-push route; de oorspronkelijke unit en ownerindex zijn behouden. De oude failure was correcte indexbescherming, geen reden om die guard te omzeilen. Een eerste echte service→queue→automatisch door timer gestarte Astra→receiver→lokale checkpoint→NEXT_ACTIONS-keten is geslaagd: runtime_reconcile/local_hourly/runs/20260926T063856Z-e43bdc98. Ook de tweede timer-canaryketen is volledig geslaagd: 20260926T064415Z-76e4c682, automatische Astra-completion en AUTO_APPLIED.json/NEXT_ACTIONS.json. Een volgende supervisor-tick herhaalde geen voltooid werk. De tijdelijke canaryunits zijn automatisch opgeruimd.

Broncommit: 28b6325 (lokaal, geen push; staged ownerentries ongewijzigd). Gerichte integratie: 38 tests geslaagd; eerder 158 relevante regressietests geslaagd. Quota-pauze/resume, crashcompletion en geërfde locks afzonderlijk met simulaties getest. Backendservices en collector-timers gezond; Linger=yes. Geen echte Windows/WSL-hostreboot of browser-origin BRIDGE_PING/PONG bewezen. Globale kwalificatie blijft daarom AUDIT_INCOMPLETE + RESIDUAL_RISK; NO_PROVEN_EDGE staat afzonderlijk. Volledige operationele details: ../codex_runtime/OPERATIONS.md en daar opgeslagen logs. Findings 024–026 zijn aanvullende lokale correctnessreparaties; de eerdere 17 reparaties blijven staan.

---

## Eerdere auditregistratie (historisch; bovenstaande aanvulling is actueler)

> FINAL QUALIFICATION: zes repaircommits en 22 repairhashes bevestigd; 475 pass / 1 socketbeperking. Default 600s-bronbeleid vastgesteld; ownerinstaller/index intact. Runtime wacht op externe WSL-evidence. Zie canonical/WSL_QUALIFICATION.md en FINAL_AUDIT_REPORT.md voor actuele kwalificatie. Oudere checkpointtekst hieronder is historisch.

# Reparatielog

## Baseline en grens

Geen productiecode gewijzigd. `git worktree add` faalt op read-only refs; coordinatorstatus faalt bij mkdir in read-only .git; `git add --dry-run -- knowledge/codex_audit` faalt op index.lock. Geen escalatie gevraagd. Dit is een filesystemblokkade, geen afwijzing door automatische approval-review.

Verplichte baselinecommit kan niet worden gemaakt. Daarom zijn alle productiereparaties BLOCKED, ook al zijn defecten bevestigd. Een tijdelijke lege Git-commit in de pytest-fixture is uitsluitend testinfrastructuur en **geen** vervangende canonical auditcommit.

## Wel uitgevoerd

Auditdocumentatie, bronhashes, read-only runtime/historische evidence, geïsoleerde suite, negen nieuwe negatieve gedragstests. Geen tests versoepeld. Geen bevinding FIXED of RETESTED genoemd.

Audit-harnessfouten: aanvankelijk ontbrak het root-importpad; daarna Path in de AST-namespace; een frozen dataclass werd in de fixture gemuteerd; de eerste regressierunner resolveerde de venv-symlink naar system-Python zonder pytest. Alleen de auditfixture is gecorrigeerd. Interpreterfout is afzonderlijk bewaard; eerste lege JSON-output is geen bewijs. Geldige uitkomsten staan in adversarial_second_pass.json en adversarial_regressions_venv.log.

## Geplande herstelvolgorde (niet uitgevoerd)

1. Baseline/audit veilig lokaal committen zonder vooraf staged werk mee te nemen; daarna eigen worktree/lease en bevroren repaircharters.
2. AUD-003/011/012: receipt-tijden, volledige coverage, executable-state en strikt prospectieve/config-identieke targets. Historische timestamps nooit achteraf verzinnen.
3. AUD-004: fail-closed economics/proof-evidence.
4. AUD-005/006/009/010: route-corruptie, JSON-typevalidatie, draftbehoud, timeout/terminal-lifecycle.
5. AUD-007/013: werkelijke contracten versus stale tests en deployment-attestatie; geen veiligheidschecks schrappen.
6. Productie hourly-blokkade oplossen met behoud/review bestaand userwerk; dan afzonderlijke runtime/DOM/recovery-canary en volledige regressie.

Geen cleanup van permanente services; auditfixture heeft geen services gestart. Tijdelijke testdirectories worden door TemporaryDirectory opgeruimd. De geïsoleerde suitekopie wordt na afsluiting verwijderd; evidence blijft in knowledge/codex_audit.

## Hervatting na baseline 80a5ff7

Baseline door eigenaar veilig gecommit en geverifieerd. Vervolgcommits/coordinator blijven read-only. Productiebronhashes ongewijzigd. Voorstellen, exacte commands en resultaten: `remediation/`. Nieuwe bevindingen AUD-CODEX-015 t/m 018; geen productiefix geclaimd. Nieuwe gedragstests: 52 passed. Breedste huidige regressie: 444 passed, 8 failed (broad_v3). De oorspronkelijke negen invarianten slagen in de voorstelkopie; oorspronkelijke rode evidence blijft bewaard.

## Actuele hervattingsstatus — 25 september 2026

Baseline 80a5ff7 is geverifieerd en veilig. Oudere tekst over ontbrekende baselinecommit is historisch; vervolgcommits/lease blijven geblokkeerd door read-only .git. Productie ongewijzigd. Zie FINAL_AUDIT_REPORT.md en remediation/TRIAGE.md: 20 bevindingen, 64 auditchecks geslaagd op voorstelbron; brede suite en duurzame replay beide 447 passed / 8 failed. Geen productie-FIXED/RETESTED. Frozen acceptancecriteria zijn niet versoepeld. Exact vervolg staat in CONTINUATION.

## Canonical herstel — 25 september 2026

De eerdere voorstelstatus is opgevolgd door echte canonical integratie op db6c0f3. Alle 17 bronbases matchten exact; userindex en niet-gerelateerde tracked bestanden zijn ongewijzigd. 64 oorspronkelijke auditchecks en nieuwe relevante suites slagen. Nieuwe bevindingen 021–023 gerepareerd en gericht hergetest. Eerste brede canonical run: 447/8; na extra safeguards 469/5, waarvan drie stale bronpatronen nu door gedragstests gedekt zijn. Definitieve hertest volgt. Geen production-deployment-PASS; Git blijft read-only. Zie canonical/canonical_change_manifest.json en canonical_changes.patch.

## Canonical eindcheckpoint

- 17 bronbases exact match; integratie per groep tests/weather/proof/bridge/executor volgens integration.jsonl.
- 64 auditchecks tegen canonical groen. Nieuwe deliverytests eerst 5 rood/2 groen, daarna 7 groen; vervolgens persistente herstart/event-before-ACK toegevoegd.
- Nieuwe falsificaties: raw upstream TimeoutError/OSError, grote integer-overflow en cityreceipt/batchvolgorde. Minimale canonical fixes; focused 25 groen.
- Drie extra static-failures na v0.4.7 waren oude literal/versiepatronen; echte storage/herstart/ACK-gedragstests behouden de veiligheidsinvariant.
- Definitieve brede canonical run: 474 passed / 2 failed. Geen skip/xfail; socket en owner-SLA afzonderlijk open.
- Git-staging/coordinator blijven read-only. Geen canonical commit gemaakt. Canonical repair ondanks die blokkade expliciet door eigenaar geautoriseerd; eigen index/diffs bewaard en niet omzeild.
- Userindex en niet-gerelateerde tracked bestanden ongewijzigd. Manual commitplan in afzonderlijke tijdelijke Gitfixture getest; zes lokale commits, unrelated staged file behouden, geen push.
- Statussen op basis van echte bron plus tests bijgewerkt; deployed runtime niet gelijkgesteld aan source.

## Definitieve externe evidence-review

Exacte run20260925T095320Z-9b5ee7a3: RESULT.json en beide logs volledig gelezen, hashes bewaard.128 offline +4 sockettests slagen. Runner-slottekst is bewust conservatief, geen failure of bug.17 canonical FIXED_AND_RETESTED blijven staan; geen reparaties herhaald. AUD-013 van residual naar HIGH CONFIRMED_OPEN op basis van exact oude deployed router/weatherhashes. AUD-002 blijft operationeel open; syncblokkade beschermt bestaande index. Geen nieuwe canonical/testbug, dus geen onnodige codewijziging of nieuwe externe test. Definitief softwareoordeel INCOMPLETE/RESIDUAL_RISK; NO_PROVEN_EDGE afzonderlijk.


## Deploymentreconciliatie 2026-09-25

Zie `runtime_reconcile/README.md`, `preservation_manifest.json`, `FINAL_PRESERVATION.json` en testlogs. Vijf deployed targets matchen exact de vóór-reparatiebasis; geen inhoudelijk ownerconflict. Payload:128 tests groen. Deployment buiten sandbox blijft uit te voeren met `runtime_reconcile/reconcile_wsl.py`; canonical/ownerbron en index intact. Hourly faalt terecht op ownerindex (exit2, geen cooldown75); het vervolgpad kan pushen en wordt niet gestart. Expliciete beleidskeuze voor no-push hourly versus bestaande synchronisatieworkflow blijft nodig. **AUDIT_INCOMPLETE + RESIDUAL_RISK**;17 canonical findings blijven FIXED_AND_RETESTED. **NO_PROVEN_EDGE** blijft afzonderlijk. Geen productie-E2E-PASS.


## Definitieve kwalificatie na externe deployment — 2026-09-25

**AUDIT_INCOMPLETE + RESIDUAL_RISK**; wetenschap afzonderlijk **NO_PROVEN_EDGE**. Dit besluit vervangt de eerdere actuele melding dat deployment nog uitgevoerd moest worden; eerdere passages blijven historische evidence. Zie `runtime_reconcile/FINAL_DECISION.md` en `FINAL_QUALIFICATION.json`. Externe run20260925T102628Z-8cb294ae: DEPLOYED_SOURCE_VERIFIED,132 tests groen, vijf huidige bronhashes correct, ownerwerk/index intact.17 canonical fixes blijven FIXED_AND_RETESTED. AUD-013: vijf-file drift verholpen; geladen browser/overige runtime blijft RESIDUAL_RISK. AUD-002: BLOCKED door correcte indexguard en onverenigbaarheid van pushende workflow met huidige autorisatie. Hourly-ketenevidence is vereist door bevroren criteria; geen scopeverlaging om PASS te geven. Geen nieuwe productiebug aangetoond, geen extra externe check vereist voor dit eindoordeel. Toekomstige hourlyhervatting vereist afzonderlijke operationele beleidskeuze. Definitieve evidence nog lokaal te committen; niets pushen.


## Laatste hourly-bereikbaarheidskwalificatie

**AUDIT_INCOMPLETE + RESIDUAL_RISK**. Bewijs: `runtime_reconcile/hourly_final_runs/20260925T104639Z-9ff94aea/RESULT.json`. Blokkade: git index is not empty: control/tampermonkey_multichat/bridge_server_v2.py, control/tampermonkey_multichat/deploy_consumer_routing_e010.py, control/tampermonkey_multichat/install_hardened_bridge.py, knowledge/candidates/MANUAL-SCOUT-HENGELTJES-20260924.json, knowledge/manual_scout_seeds/2026-09-24-hengeltjes-late-passive-liquidity.md. Geen productie-E2E uitgevoerd of PASS gesimuleerd. Oorspronkelijke guards behouden; geen push/handel/API. NO_PROVEN_EDGE afzonderlijk.
