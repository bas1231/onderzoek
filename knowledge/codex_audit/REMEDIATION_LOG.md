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
