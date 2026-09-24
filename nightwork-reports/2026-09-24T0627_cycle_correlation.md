# Nachtwerk — local cycle correlation hardening

Timestamp: 2026-09-24 06:27 CEST
Economic default: `NO_PROVEN_EDGE`

## Nieuwe voortgang
Na 05:30 verscheen geen nieuwe lokale request op `ai/runtime-exchange`; de laatste requestcommit blijft `hourly-20260923T140000+0200`. Dat is geen bewijs van een storing, maar betekent dat verse lokale timer/exchange-liveness nog niet uit Git kan worden afgeleid.

De bestaande schedulerroute is daarom zonder nieuw subsystem uitgebreid met één bounded lokale correlatiereceipt. `edge_hunter_cycle.py` schrijft na succesvolle hourly cycle, Edge Hunter en alle drie verplichte checkpoints atomair `scheduled-cycle-latest.json` met het canonieke `run_id` en de waargenomen Git-checkpointstatus/head. Een mislukking vóór het einde schrijft geen COMPLETED-receipt.

`runtime_health.py` consumeert die receipt fail-closed. Alleen een geldige, recente `PVA_SCHEDULED_CYCLE_RECEIPT_V1` naast een recente READY preflight promoveert de classificatie naar `RECENT_CYCLE_COMPLETED`. Ook dan blijven `scheduler_service_running`, `browser_bridge_running` en `runtime_exchange_running` expliciet false: dit is completion-evidence, geen continue livenessclaim. Stale of malformed receipts degraderen naar `RECENT_PREFLIGHT`.

## Gewijzigde commits
- `39b4ad8d` — scheduler wrapper schrijft atomische cycle-correlatiereceipt.
- `2b096df2` — runtime health correleert receipt en run_id zonder false-UP claim.
- `1ff8c8f0` — regressietests voor recent/stale/malformed correlation.
- dit rapport — auditstatus.

## Tests
Nieuwe unitcases zijn toegevoegd voor:
1. verse preflight + verse geldige cycle receipt => `RECENT_CYCLE_COMPLETED`;
2. stale cycle receipt => geen upgrade boven `RECENT_PREFLIGHT`;
3. malformed receipt => fail-closed preflight-only;
4. zelfs bij completion blijven continuous-running claims false.

De tests zijn repository-side toegevoegd maar in deze automation niet lokaal uitgevoerd; test-execution is daarom **UNVERIFIED**, niet PASS.

## Runtime-evidence
- Durable native research cycle + report + Git commit: **PASS** uit vorige run.
- Nieuwe lokale exchange request na 2026-09-23 14:00 CEST: **NIET WAARGENOMEN**.
- Verse lokale timer-trigger/cycle receipt: **UNVERIFIED**.
- Live WSL/systemd/browser/bridge/exchange process-state: **UNVERIFIED**.

## End-state checklist
- Bridge server SENT/ACK filtering: **PASS repository/tests; live UNVERIFIED**
- Browser duplicate/stale replay hardening: **PASS repository/tests; live UNVERIFIED**
- Scheduler complete-cycle control flow: **PASS repository-code; live UNVERIFIED**
- Scheduler cycle-id correlation: **PASS design/code; test execution + live receipt UNVERIFIED**
- Scheduler timer liveness: **UNVERIFIED**
- Runtime exchange polling/liveness: **UNVERIFIED**
- Scouts: **PASS durable native cycle; local runtime UNVERIFIED**
- Recon: **PASS durable native cycle; local runtime UNVERIFIED**
- Specialist dispatch: **PASS durable native cycle; local runtime UNVERIFIED**
- Red-team/reproducer gate: **PASS durable native cycle**
- Reporting: **PASS**
- Git persistence: **PASS**
- Health/recovery: **PARTIAL PASS code-side; live restart/cycle canary UNVERIFIED**
- Full local timer -> cycle -> exchange/report -> Git checkpoint: **UNVERIFIED**

## Blockers
De remote/GitHub-side bewijsroute is nu voorbereid om de eerstvolgende natuurlijke lokale cycle ondubbelzinnig aan één `run_id` te koppelen. Het resterende blocker is feitelijke lokale uitvoering van de bijgewerkte `main` en daarna een natuurlijke timer-trigger. Git alleen kan niet bewijzen dat de lokale checkout de nieuwe commits al heeft of dat systemd actief is.

## Exact volgende stap
Bij eerstvolgende verse lokale evidence controleer dezelfde `run_id` in `scheduled-cycle-latest.json`, canonical run manifest, hourly report en Git-checkpoint. Alleen die componenten promoveren naar PASS. Als geen receipt verschijnt nadat de lokale checkout aantoonbaar de nieuwe commits bevat, is pas dan een concrete lokale systemd/sync-diagnose gerechtvaardigd. Geen live trading, betaalde acties, wallet-acties of OpenAI-API-kosten.