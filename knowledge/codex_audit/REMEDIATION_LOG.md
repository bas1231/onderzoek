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
