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
