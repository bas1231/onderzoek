# Nachtwerkrapport — 2026-09-23 23:25 Europe/Amsterdam

## Scope
Prioriteit 1: bridge/result-delivery. Scheduled-worker contract is eerst gelezen. Geen claim dat lokale WSL/runtime UP/RUNNING is zonder runtime-evidence.

## Nieuwe wijziging
- `control/tampermonkey_multichat/test_bridge_server_hardened.py` toegevoegd in commit `87afb26d21d0293096ebe1ca93b25a5f856f8e50`.
- Regression coverage voor: RESULT_READY/raw WSL compaction + bounded browser payload; normale PING-preservatie; task-level stale duplicate in OUTBOX wordt retired wanneer dezelfde task_id al in SENT staat.
- Bestaande hardened server blijft de reparatieroute; geen nieuw subsystem gebouwd.

## Bewijs / tests
- STATIC REVIEW PASS: `bridge_server_hardened.py` bevat server-side SENT task-id dedupe, bounded 256-loop, raw-result compaction, max browser message 900 en authenticated `/health`.
- TEST CODE ADDED: offline unittest-suite toegevoegd. Vanuit deze GitHub-only automation kan de Python-suite niet lokaal worden uitgevoerd; runtime-resultaat daarom UNVERIFIED, niet PASS.
- CANARY DESIGN PASS: gewone kleine `PING canary` blijft ongewijzigd door compaction; geen grote capability probe nodig.

## Runtime-evidence
- GitHub main toont nieuwe remote commits en code, maar dit bewijst niet dat WSL/service/browser lokaal draait.
- Lokale bridge process state: UNVERIFIED.
- Lokale scheduler process state: UNVERIFIED.
- Runtime-exchange historische geldige requests bewijzen eerdere activiteit, niet huidige liveness.

## End-state checklist
| Onderdeel | Status | Bewijs / blocker |
|---|---|---|
| Bridge server-side duplicate suppression | PASS (code) / UNVERIFIED (runtime) | hardened wrapper + regression test |
| Browser-side dedupe/restart/DOM virtualisatie | UNVERIFIED | volgende inspectie van actuele userscript/patch state nodig |
| Scheduler | UNVERIFIED | geen directe lokale runtime-evidence in deze automation |
| Runtime exchange contract | PASS (remote contract) / UNVERIFIED (current liveness) | fail-closed contract aanwezig |
| Scouts | UNVERIFIED runtime | registry/contracts aanwezig |
| Recon | UNVERIFIED runtime | role/contracts aanwezig; eerdere Git outputs bestaan |
| Specialist dispatch | UNVERIFIED runtime | contractueel aanwezig |
| Red-team/reproducer gate | UNVERIFIED runtime | contractueel aanwezig |
| Reporting | PASS (Git persistence) | hourly/nightwork outputs kunnen duurzaam worden gecommit |
| Git persistence | PASS | commit `87afb26d...` |
| Health/recovery | PARTIAL | `/health` code aanwezig; live health niet bereikbaar vanuit GitHub-only automation |

## Blockers
1. Geen directe toegang vanuit deze automation tot localhost/WSL/systemd/browser; huidige liveness kan niet eerlijk als RUNNING worden geclaimd.
2. Browser-side actuele dedupe/restart-state moet nog remote worden geïnventariseerd en waar nodig regressiegedekt.
3. Scheduler/runtime-exchange oorzaakanalyse moet doorgaan vanuit remote code/config; alleen wanneer uiteindelijk een lokale verificatiestap werkelijk onvermijdelijk is, wordt die als concrete gebruikersactie gemeld.

## Exact volgende stap
Inspecteer op `main` de actuele Tampermonkey/userscript delivery-state en scheduler/runtime-exchange code/config. Voeg eerst remote regressiedekking toe voor stale replay/restart en scheduler-idle/idempotentie voordat een lokale handmatige stap wordt gevraagd.

Economic default: `NO_PROVEN_EDGE`.
