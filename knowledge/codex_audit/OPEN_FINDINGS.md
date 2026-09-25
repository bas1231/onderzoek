# Actuele bevindingen na canonical herstel

17 FIXED_AND_RETESTED; 1 CONFIRMED_OPEN; 1 BLOCKED; 3 RESIDUAL_RISK; 1 UNPROVEN. Softwarebron gerepareerd; volledige systeemkwalificatie FAIL/INCOMPLETE, NO_PROVEN_EDGE.

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

Resterende suitefailures: socket PermissionError en onbeslist 15s/600s installerbeleid. Zie FINAL_AUDIT_REPORT.md en canonical/COMMIT_PLAN.md.
