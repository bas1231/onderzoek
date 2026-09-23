# Prediction Research-OS nachtwerk — 2026-09-24 01:29 CEST

## Scope
Prioriteit 1: duplicate/stale RESULT_READY-delivery.

## Bevinding
`control/browser_extension/content.js` heeft een duurzame pending-result-ACK queue en retry/backoff, maar `pollOutbox()` controleert die queue pas **nadat** `insertAndSend(resultMessage(item))` is uitgevoerd. Als het resultaat al naar ChatGPT is gestuurd en de `/ack` nog pending is, kan `/outbox` dezelfde task opnieuw aanbieden en kan de browser hem opnieuw versturen. Dit is de resterende concrete browser-side duplicate-dump race.

## Wijzigingen
- `control/browser_extension/patch_result_ack_presend_gate.py`
  - idempotente, fail-closed migratie voor de bestaande `content.js` route;
  - voegt vóór `insertAndSend()` een `resultAckPending(task_id)` gate toe;
  - probeert eerst de duurzame ACK opnieuw te flushen en verstuurt het resultaat niet opnieuw zolang de ACK pending is;
  - weigert onbekende/stale broncode te patchen als de geaudite anchor niet exact aanwezig is.
- `tests/bridge/test_result_ack_presend_patch.py`
  - regressietest voor pre-send ordering;
  - idempotentie;
  - fail-closed gedrag bij source drift.

Commits: `ac265edb6e2b5fef0ca39170648eafdaf30841fc`, `f29a7616f3b2fb494af9a8a2da477a1e2dfb9a82`.

## Tests
De regressietests zijn in Git vastgelegd maar vanuit deze GitHub-only automation niet lokaal uitgevoerd. Daarom: **UNVERIFIED_RUNTIME**, niet PASS. De patch zelf is bewust nog niet als bewijs van een draaiende browser-extension beschouwd.

## Runtime-evidence
Geen directe WSL/browser/systemd-evidence beschikbaar in deze run. Een GitHub-commit bewijst geen lokale deployment of liveness.

## End-state checklist
- Bridge server-side SENT/ACK filtering: PASS (eerder statisch/unitmatig onderbouwd; geen nieuwe regressie gezien)
- Browser duplicate-result pre-send bescherming: FAIL in huidige `content.js`; PATCH READY en fail-closed getest-op-ontwerp, nog niet lokaal toegepast/bewezen
- Browser stale/restart replay: PARTIAL; durable ACK queue bestaat, pre-send gate is nu als idempotente migratie klaar
- Scheduler: UNVERIFIED live
- Runtime exchange: UNVERIFIED live
- Scouts: UNVERIFIED live
- Recon: UNVERIFIED live
- Specialist dispatch: UNVERIFIED live
- Red-team/reproducer gate: UNVERIFIED live
- Reporting: PASS voor Git-persistence van nachtwerkrapporten; automatische lokale cyclus UNVERIFIED
- Git persistence: PASS
- Health/recovery: PARTIAL; fail-closed patchpad aanwezig, live canary nog UNVERIFIED

## Blocker
De automation kan de lokale checkout/browser-extension niet rechtstreeks bereiken. Daarom is het onveilig om te claimen dat de patch lokaal actief is. Er is nog geen gebruikersactie nodig: eerst moet de remote-side migratie/deploymentroute verder worden gekoppeld aan de bestaande sync/recoveryflow zonder lokale vooruitlopende wijzigingen te overschrijven.

## Exact volgende stap
Inspecteer de bestaande runtime-sync/recoveryroute en koppel deze idempotente migratie alleen wanneer de lokale source overeenkomt met de geaudite anchor. Voeg daarna een kleine PING/canary en statusmanifest toe waarmee een volgende run lokale toepassing en liveness kan onderscheiden van alleen Git-state. Pas daarna scheduler/runtime-exchange aanpakken.

Economische conclusie: `NO_PROVEN_EDGE`.
