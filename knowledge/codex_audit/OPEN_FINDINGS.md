# Open bevindingen

- AUD-CODEX-001 — HIGH / BLOCKED: Verplichte lokale auditcommit en coordinatorregistratie onmogelijk binnen huidige sandbox.
- AUD-CODEX-002 — HIGH / CONFIRMED: Actuele runtime-sync is geblokkeerd door bestaande staged wijzigingen; laatste wrapperreceipt is verouderd.
- AUD-CODEX-003 — HIGH / CONFIRMED: Beide weatherrecorders gebruiken request-start als retrieved_at; KWI deelt één eerdere tijd over drie seriële fetches.
- AUD-CODEX-004 — HIGH / CONFIRMED: Proof-gate accepteert negatieve, nul en niet-numerieke netto-edge plus null kostenvelden.
- AUD-CODEX-005 — HIGH / CONFIRMED: Corrupt bestaande route wordt als geslaagde nieuwe route geretourneerd zonder duurzame route te schrijven.
- AUD-CODEX-006 — MEDIUM / CONFIRMED: Geldige JSON met niet-objecttopniveau laat handler crashen zonder HTTP-foutresponse.
- AUD-CODEX-007 — MEDIUM / CONFIRMED: Repositorybrede tests zijn niet groen; meerdere tests volgen oude interfaces/versies.
- AUD-CODEX-008 — HIGH / UNPROVEN: Gevonden weatherlane bewijst geen 1–4 uur probabilistische voorspelling van definitieve TWC-settlement.
- AUD-CODEX-009 — HIGH / CONFIRMED: Canonical userscript overschrijft bestaand onverzonden gebruikersconcept bij bridgelevering.
- AUD-CODEX-010 — HIGH / CONFIRMED: Timeout met partiële bytes-output faalt tijdens timeoutafhandeling en verliest normaal RESULT-contract.
- AUD-CODEX-011 — HIGH / CONFIRMED: Interne websocket-meetgaten en ontbrekende executable prijzen worden als bewezen geen reactie geclassificeerd.
- AUD-CODEX-012 — HIGH / CONFIRMED: Prospectieve evaluator accepteert target dat al voor voorspelling compleet was, ook bij andere config.
- AUD-CODEX-013 — MEDIUM / RESIDUAL_RISK: Geinstalleerde componenten gebruiken verschillende repositories en userscript wijkt af van canonical Git-bestand.

Geen bevinding FIXED/RETESTED. Zie FINAL_AUDIT_REPORT.md.

- AUD-CODEX-014 — LOW / RESIDUAL_RISK: 14 historische Pythonjobs syntactisch ongeldig; bewaar failure-evidence en voorkom blind hergebruik.
