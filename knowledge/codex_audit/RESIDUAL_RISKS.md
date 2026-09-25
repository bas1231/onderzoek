# Definitieve residuele risico's

## Bevestigde operationele blockers

- AUD-013: deployed router en drie weatherbronnen matchen oude defecte baselinehashes. Canonical bron is gerepareerd; artifactdeployment naar buiten de writable workspace is niet uitgevoerd. Geïnstalleerde gebruikersscriptversie verschilt; geladen browserversie onbekend.
- AUD-002: hourly failed en completed receipt circa19,82uur oud tijdens externe run. Sync/checkpoint weigeren terecht bij ownerwerk/divergentie. Die guards niet verwijderen om PASS te krijgen.

## Resterende onzekerheden

- Werkelijke productie browser→Director→executor→resultaat→browserketen en reboot/recovery zijn niet getest. Tijdelijke socket-/serverrebindtests zijn geen vervanging.
- Executor NRestarts1293 is cumulatief; één snapshot bewijst geen actuele crashloop. Running0 en active-status bewijzen geen nuttige nieuwe taakuitvoering.
- Oneshoot weather inactive/dead is op zichzelf geen fout. Actuele timer/collectorcontinuïteit niet uit die velden afleiden.
- Bron-default600s staat vast; actieve override niet uit ontbrekend healthveld afleiden. Ownerinstaller blijft staged en behouden.
- Volledige TWC/forecast/PIT/holdout- en economische bewijsvoering blijft UNPROVEN/NO_PROVEN_EDGE, los van softwarekwalificatie.
- Nieuwe eindrapportage nog lokaal te committen; zes canonical repaircommits geverifieerd. Geen push nodig voor auditvastlegging; niet proberen runtime-sync te forceren onder no-push/ownerbehoudrestricties.

De sandbox-socketbeperking is extern opgeheven:128 offline en4 echte loopbacktests groen. Die beperking is geen resterende productiebug. Geen kwalificatierunnerdefect aangetoond.


## Deploymentreconciliatie 2026-09-25

Zie `runtime_reconcile/README.md`, `preservation_manifest.json`, `FINAL_PRESERVATION.json` en testlogs. Vijf deployed targets matchen exact de vóór-reparatiebasis; geen inhoudelijk ownerconflict. Payload:128 tests groen. Deployment buiten sandbox blijft uit te voeren met `runtime_reconcile/reconcile_wsl.py`; canonical/ownerbron en index intact. Hourly faalt terecht op ownerindex (exit2, geen cooldown75); het vervolgpad kan pushen en wordt niet gestart. Expliciete beleidskeuze voor no-push hourly versus bestaande synchronisatieworkflow blijft nodig. **AUDIT_INCOMPLETE + RESIDUAL_RISK**;17 canonical findings blijven FIXED_AND_RETESTED. **NO_PROVEN_EDGE** blijft afzonderlijk. Geen productie-E2E-PASS.


## Definitieve kwalificatie na externe deployment — 2026-09-25

**AUDIT_INCOMPLETE + RESIDUAL_RISK**; wetenschap afzonderlijk **NO_PROVEN_EDGE**. Dit besluit vervangt de eerdere actuele melding dat deployment nog uitgevoerd moest worden; eerdere passages blijven historische evidence. Zie `runtime_reconcile/FINAL_DECISION.md` en `FINAL_QUALIFICATION.json`. Externe run20260925T102628Z-8cb294ae: DEPLOYED_SOURCE_VERIFIED,132 tests groen, vijf huidige bronhashes correct, ownerwerk/index intact.17 canonical fixes blijven FIXED_AND_RETESTED. AUD-013: vijf-file drift verholpen; geladen browser/overige runtime blijft RESIDUAL_RISK. AUD-002: BLOCKED door correcte indexguard en onverenigbaarheid van pushende workflow met huidige autorisatie. Hourly-ketenevidence is vereist door bevroren criteria; geen scopeverlaging om PASS te geven. Geen nieuwe productiebug aangetoond, geen extra externe check vereist voor dit eindoordeel. Toekomstige hourlyhervatting vereist afzonderlijke operationele beleidskeuze. Definitieve evidence nog lokaal te committen; niets pushen.


## Laatste hourly-bereikbaarheidskwalificatie

**AUDIT_INCOMPLETE + RESIDUAL_RISK**. Bewijs: `runtime_reconcile/hourly_final_runs/20260925T104639Z-9ff94aea/RESULT.json`. Blokkade: git index is not empty: control/tampermonkey_multichat/bridge_server_v2.py, control/tampermonkey_multichat/deploy_consumer_routing_e010.py, control/tampermonkey_multichat/install_hardened_bridge.py, knowledge/candidates/MANUAL-SCOUT-HENGELTJES-20260924.json, knowledge/manual_scout_seeds/2026-09-24-hengeltjes-late-passive-liquidity.md. Geen productie-E2E uitgevoerd of PASS gesimuleerd. Oorspronkelijke guards behouden; geen push/handel/API. NO_PROVEN_EDGE afzonderlijk.
