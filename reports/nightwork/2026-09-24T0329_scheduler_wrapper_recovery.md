# Nachtwerkrapport — 2026-09-24 03:29 Europe/Amsterdam

## Doel
Prioriteit 2: scheduler/runtime-exchange/orchestratie betrouwbaar en aantoonbaar maken, met fail-closed crash/restartgedrag en zonder Git-configuratie als live runtimebewijs te presenteren.

## Kritieke bevinding
De systemd service start `control/hourly/edge_hunter_cycle.py`. Die wrapper gebruikte `runpy.run_path(... hourly_cycle.py, run_name="__main__")`. `hourly_cycle.py` eindigt met `raise SystemExit(main())`; ook bij succesvolle `main() == 0` beëindigt dat de wrapper onmiddellijk. Daardoor was alle code ná die regel structureel onbereikbaar: Edge Hunter `prepare()`, asset-fill checkpoint, KWI checkpoint en het afsluitende durable Git-checkpoint draaiden via deze schedulerroute niet. Een rc=0 kon dus ten onrechte een complete succesvolle cyclus suggereren.

Daarnaast selecteerde de wrapper de nieuwste `knowledge/runs/hourly-*.json` puur op mtime, waardoor een derivative JSON dezelfde glob kon winnen. En checkpoint-subprocess failures werden alleen geprint en vervolgens als succesvolle service-run gemaskeerd.

## Wijzigingen
- `04068c4`: `control/hourly/edge_hunter_cycle.py`
  - laadt `hourly_cycle.py` als module en roept `hourly.main()` direct aan, zodat succesvolle uitvoering niet meer via `SystemExit(0)` de wrapper afkapt;
  - behandelt cadence rc=75 expliciet als cooldown/no-work;
  - selecteert alleen een canonical run manifest waarvan `data.run_id == filename stem` en `status` aanwezig is;
  - asset-fill, KWI en Git-checkpoint zijn required checkpoints: nonzero rc wordt nu zichtbaar als failure in plaats van stil succes.
- `041ef6f`: systemd unit accepteert uitsluitend rc=75 aanvullend als succesvolle no-work/cooldown-state (`SuccessExitStatus=75`).
- `6b5a8c5`: regressietest `tests/hourly/test_edge_hunter_cycle_scheduler.py` bewaakt early-exit, cooldown-semantiek, canonical-manifestselectie en checkpoint failure propagation.

## Tests / bewijs
- Nieuwe regressietest is duurzaam op `main` vastgelegd.
- Python-source is AST-parsebaar volgens de testcontracten; er is vanuit deze automation geen lokale pytest-runtime beschikbaar, dus uitvoering van de test is `UNVERIFIED`.
- GitHub Actions toont momenteel 0 workflow-runs op `main`; CI levert dus geen aanvullend runtimebewijs.
- De systemd timerconfig staat op ieder heel uur met `Persistent=true`, maar configuratie is geen bewijs dat de lokale timer enabled/running is.

## Runtime-evidence
Geen directe toegang tot lokale WSL/systemd in deze run. Daarom geen `UP/RUNNING`-claim voor scheduler, bridge of runtime exchange. De gevonden schedulerbug is code-side gerepareerd, maar toepassing door de lokale runtime vereist een toekomstige succesvolle `runtime_sync.py` fast-forward of ander aantoonbaar lokaal bewijs.

## End-state checklist
| Onderdeel | Status | Bewijs / blocker |
|---|---|---|
| Bridge server-side SENT/ACK replay filtering | PASS (code/tests) / UNVERIFIED live | eerdere hardening aanwezig; geen verse lokale evidence |
| Browser duplicate-result pre-send gate | PASS (remote recovery path) / UNVERIFIED live | forward-only migratie aanwezig |
| Scheduler wrapper control flow | PASS (code contract) / UNVERIFIED live | early-SystemExit bug verwijderd; required checkpoints fail closed |
| Scheduler timer | UNVERIFIED live | timerconfig aanwezig, geen systemd runtime-status |
| Runtime exchange | UNVERIFIED live | Git transportcontract aanwezig, geen verse lokale request/response-liveness bewezen deze run |
| Scouts | UNVERIFIED live | architectuur aanwezig |
| Recon | UNVERIFIED live | architectuur aanwezig |
| Specialist dispatch | UNVERIFIED live | architectuur aanwezig |
| Red-team/reproducer gate | UNVERIFIED live | architectuur aanwezig |
| Reporting | PASS (Git persistence) | dit auditrapport is duurzaam op `main` |
| Git persistence | PASS | commits `04068c4`, `041ef6f`, `6b5a8c5` + dit rapport |
| Health/recovery | PARTIAL | scheduler failures zijn nu zichtbaar; expliciete runtime health receipt/liveness-classificatie nog te auditen |

## Blockers
Geen gebruikersactie nodig. Voor een live PASS ontbreekt verse lokale systemd/runtime-evidence. Remote-side kan nog verder worden verbeterd door de bestaande health/statusroute expliciet onderscheid te laten maken tussen configured, last-success, cooldown, stale/idle en blocked.

## Exact volgende stap
Audit en versterk bestaande scheduler/runtime health-status en exchange-liveness zonder een nieuw los subsysteem te bouwen. Voeg idempotente crash/restart-tests toe voor request publication/response ingest en bewijs daarna, zodra lokale evidence beschikbaar komt, één volledige timer→cycle→request/response→report→Git-checkpoint keten.

Economische conclusie blijft `NO_PROVEN_EDGE`.
