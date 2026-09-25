# Triage van alle oorspronkelijke failures

Status 2026-09-25. Alle wijzigingen hieronder betreffen uitsluitend de geïsoleerde voorstelkopie. Canonical tests en productiecode zijn ongewijzigd. Geen skip/xfail toegevoegd.

| Oorspronkelijke failure | Aantal | Classificatie en besluit |
|---|---:|---|
| test_warrant_issuer: issued warrant accepted | 1 | Ongeldige/onvolledige fixture: verplichte AUTONOMOUS_BUILD_POLICY ontbreekt. Fixture aangevuld; autorisatieassertion behouden. |
| test_research_os_six_domain_e007: registry version | 1 | Stale test: registry v4, test verwacht v3. Verwachting geactualiseerd; rollen/invarianten behouden. |
| test_market_reaction: WS sequence gap | 1 | Stale interface: controle verhuisd van tickerboek naar subscription sid. Test richt zich nu op echte sequence-validator. |
| test_market_reaction_ws: vijf handle_message-tests | 5 | Stale signature/sid/tracker-fixtures. Tracker en sid toegevoegd. Sequencegap hoort raise+capture_gap en geen nieuwe state te geven; assertion aangepast aan abort-contract. |
| test_bridge_server_sent_semantics | 1 | Omgevingsbeperking: socket bind krijgt PermissionError. Niet overgeslagen of als PASS geteld. Werkelijke HTTP ACK-idempotentie blijft UNPROVEN. |
| test_install_hardened_bridge_fast_deadman_static | 1 | Vooraf bestaand conflict tussen 15s-test en staged eigenaarinstaller met 600s inactivitybeleid. Bron niet overschreven; beoogde runtime-SLA UNPROVEN. |
| test_patch_v045_task_dedupe_static: normal ACK | 1 | False positive: zoekactie trof wake_old-literal in patchgenerator in plaats van wake_new. Zoekscope gecorrigeerd; assertion taskmemory vóór ACK ongewijzigd. |
| test_userscript_v046_guard_static | 6 | Bron/deploymentmismatch: test verwacht v0.4.6, canonical v0.3.3. Exacte version/identifier-assertions zijn geen zelfstandige gedragsbewijzen. Draftbehoud en deliverybevestiging krijgen echte Node-tests; taskdedupe/retry/backoff/page-recovery blijven onvoldoende bewezen. Alle zes failures blijven zichtbaar. |
| **Totaal baseline** | **17** | Geen blanketclassificatie als onschadelijk. |

## Twee extra failures na v1

- Receiptfixture mist nieuw timestamp_semantics-contract: alleen synthetische fixture gemarkeerd; oude echte manifests nooit aangepast. Positieve eligibilitytest behouden; nieuwe negatieve test sluit legacy manifests uit.
- Quiet-WS positive test had twee coveragepunten met 30,5s gat bij maximaal 5s toegestaan: fixture maakt nu expliciet continue coverage. Onafhankelijke gaptest behoudt oorspronkelijke counterexample en eist UNPROVEN.

## Negen oorspronkelijke auditreproducties

Alle negen bevestigen productiegebreken; geen false positives: request-start/receipt KWI, request-start/receipt TWC, corrupte route, JSON-array, timeoutbytes, coveragegat, lege executable baseline, eerdere/cross-config target en ongeldige proof-economics worden afgedekt door de oorspronkelijke regressies/harness (zie exacte testnamen in evidence/test_audit_regressions.py). De negende pytest-invariant controleert composerbehoud (AUD-009); KWI en TWC delen één receiptassertion. Harness uitsluitend technisch compleet gemaakt voor succesvolle timeouttak; veiligheidsassertions niet versoepeld.

De negen pytest-invarianten slagen op voorstelbron; oorspronkelijke rode logs zijn behouden. Aanvullend 55 tests, samen 64 auditchecks. Baseline-defecten zijn hiermee niet in productie opgelost.

## Tweede ronde

Nieuwe bevindingen 015–020 en de voorstelregressie 017 zijn afzonderlijk vastgelegd in FINDINGS.jsonl. Policy-denial kreeg eerst eigen rode test. False delivery en invalid/foreign post-state kregen drie rode tests vóór patch. Tweede review door dezelfde auditor met nieuwe counterexamples; geen claim van onafhankelijke menselijke of tweede-modelreview.
