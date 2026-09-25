# Open bevindingen — hervatting 25 september 2026

**AUDIT_FAIL + AUDIT_INCOMPLETE + NO_PROVEN_EDGE.** Baseline 80a5ff7 intact. Geen productieherstel; .git/coordinator blijven read-only. 64 auditgedragstests slagen op voorstelbron; volledige geselecteerde suite 447 passed / 8 failed.

| ID | Severity | Status | Bevinding |
|---|---|---|---|
| AUD-CODEX-001 | HIGH | BLOCKED | Baseline 80a5ff7 door eigenaar gecommit; vervolgauditcommits en gedeelde coordinator nog steeds geblokkeerd door read-only .git. |
| AUD-CODEX-002 | HIGH | CONFIRMED | Actuele runtime-sync is geblokkeerd door bestaande staged wijzigingen; laatste wrapperreceipt is verouderd. |
| AUD-CODEX-003 | HIGH | CONFIRMED | Beide weatherrecorders gebruiken request-start als retrieved_at; KWI deelt één eerdere tijd over drie seriële fetches. |
| AUD-CODEX-004 | HIGH | CONFIRMED | Proof-gate accepteert negatieve, nul en niet-numerieke netto-edge plus null kostenvelden. |
| AUD-CODEX-005 | HIGH | CONFIRMED | Corrupt bestaande route wordt als geslaagde nieuwe route geretourneerd zonder duurzame route te schrijven. |
| AUD-CODEX-006 | MEDIUM | CONFIRMED | Geldige JSON met niet-objecttopniveau laat handler crashen zonder HTTP-foutresponse. |
| AUD-CODEX-007 | MEDIUM | CONFIRMED | Repositorybrede tests zijn niet groen; meerdere tests volgen oude interfaces/versies. |
| AUD-CODEX-008 | HIGH | UNPROVEN | Gevonden weatherlane bewijst geen 1–4 uur probabilistische voorspelling van definitieve TWC-settlement. |
| AUD-CODEX-009 | HIGH | CONFIRMED | Canonical userscript overschrijft bestaand onverzonden gebruikersconcept bij bridgelevering. |
| AUD-CODEX-010 | HIGH | CONFIRMED | Timeout met partiële bytes-output faalt tijdens timeoutafhandeling en verliest normaal RESULT-contract. |
| AUD-CODEX-011 | HIGH | CONFIRMED | Interne websocket-meetgaten en ontbrekende executable prijzen worden als bewezen geen reactie geclassificeerd. |
| AUD-CODEX-012 | HIGH | CONFIRMED | Prospectieve evaluator accepteert target dat al voor voorspelling compleet was, ook bij andere config. |
| AUD-CODEX-013 | MEDIUM | RESIDUAL_RISK | Geinstalleerde componenten gebruiken verschillende repositories en userscript wijkt af van canonical Git-bestand. |
| AUD-CODEX-014 | LOW | RESIDUAL_RISK | 14 van 726 Pythonbestanden hebben syntaxfouten; historische mislukte jobs mogen niet als opnieuw uitvoerbaar worden behandeld. |
| AUD-CODEX-015 | HIGH | CONFIRMED | Productie-executor importeert ontbrekende policy_check-module. |
| AUD-CODEX-016 | MEDIUM | CONFIRMED | Malformed HTTP200 van upstream wordt als succes doorgegeven. |
| AUD-CODEX-017 | MEDIUM | RESIDUAL_RISK | Eerste draftbehoudpatch strandde eigen invoer na ontbrekende sendknop. |
| AUD-CODEX-018 | HIGH | CONFIRMED | Policy-afgewezen taak blijft in RUNNING-directory achter. |
| AUD-CODEX-019 | HIGH | CONFIRMED | Leeg invoerveld wordt zonder nieuwe userturn als geslaagde levering behandeld. |
| AUD-CODEX-020 | HIGH | CONFIRMED | Foreign ticker en niet-eindige post-event prijs worden als reactie gescoord. |

Zie remediation/TRIAGE.md voor alle 17 oorspronkelijke failures en FINAL_AUDIT_REPORT.md voor CONTINUATION. Voorstel-PASS is geen productie-PASS.
