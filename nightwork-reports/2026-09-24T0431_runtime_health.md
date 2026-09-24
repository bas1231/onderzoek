# Nachtwerk — runtime health/liveness

Timestamp: 2026-09-24 04:31 CEST
Economic default: `NO_PROVEN_EDGE`

## Wijzigingen
- `control/hourly/runtime_health.py`: nieuwe bounded classifier bovenop bestaande runtime-sync/checkpoint receipts; geen nieuw subsystem.
- `tests/test_runtime_health.py`: regressies voor missing, recent READY, stale READY, BLOCKED en malformed timestamp.
- `control/hourly/systemd/prediction-research-hourly-director.service`: `ExecStartPost` schrijft health receipt na succesvolle/cooldown cycle.

Commits: `281c83c`, `c46acd0`, `1ffa0d0`.

## Waarom
Repository-state kon alleen `UNVERIFIED` zeggen. De scheduler had al lokale receipts, maar geen expliciete semantiek die `READY` onderscheidt van daadwerkelijke process-liveness. De classifier maakt nu vier states zichtbaar: `RECENT_PREFLIGHT`, `STALE_IDLE`, `BLOCKED`, `UNVERIFIED`. `RECENT_PREFLIGHT` is bewust geen `UP/RUNNING` claim. Afwezigheid van exchange-work blijft geen storing.

## Tests / bewijs
Statische/unit-regressies zijn toegevoegd, maar vanuit deze GitHub-automation is de lokale pytest-run niet uitvoerbaar; test-executie blijft `UNVERIFIED` tot lokaal/CI bewijs verschijnt. De timerconfiguratie op `*:00:00`, `Persistent=true`, `AccuracySec=30s` is repository-evidence, geen bewijs dat systemd live draait. De laatste Git-state bevat historische research-output, maar dat bewijst evenmin huidige WSL-liveness.

## End-state checklist
- Bridge server-side SENT/ACK filtering: **PASS (repository/tests)**
- Bridge browser duplicate/stale replay hardening: **PASS (repository/tests), live UNVERIFIED**
- Scheduler wrapper complete-cycle control flow: **PASS (repository/tests), live UNVERIFIED**
- Scheduler timer liveness: **UNVERIFIED**
- Runtime exchange current polling/liveness: **UNVERIFIED**
- Runtime health classification: **PASS (code contract), execution UNVERIFIED**
- Scouts: **UNVERIFIED live**
- Recon: **UNVERIFIED live**
- Specialist dispatch: **UNVERIFIED live**
- Red-team/reproducer gate: **UNVERIFIED live**
- Reporting path: **PASS repository-side; automatic local cycle UNVERIFIED**
- Git persistence/checkpoint: **PASS code-side; current local execution UNVERIFIED**
- Crash/restart recovery: **PARTIAL PASS code-side; live canary UNVERIFIED**

## Blockers
Geen nieuwe gebruikersactie nodig. Het enige resterende bewijs voor `UP/RUNNING` moet uit de lokale runtime zelf komen: een verse timer-trigger die runtime-sync/health receipts produceert en vervolgens een volledige cycle + durable Git checkpoint oplevert. Remote code mag dat bewijs niet simuleren.

## Exact volgende stap
Inspecteer in de volgende run of een verse `PVA_RUNTIME_HEALTH_V1`/runtime-sync receipt indirect via nieuwe Git/runtime-exchange evidence zichtbaar is. Als dat bewijs ontbreekt, werk remote-side verder aan één fail-closed end-to-end canary/receipt die timer -> cycle -> exchange/report -> Git checkpoint correleert zonder commandmarker of grote capability probe.
