# Reliability Gate

Overall status: UNVERIFIED_LIVE

## Proven from repository/test evidence

- Historical autonomous execution evidence: E080 PASS
- Pre-discover parse-failure incident path: PASS
- DISCOVERED-timeout incident path: PASS
- Incident-to-chat wake-up path: PASS
- Paid/live/wallet actions remain disabled by policy/guardrails
- Bridge result ACK state is persisted and reconciled against lifecycle state

## Not proven by a Git commit

The following MUST NOT be reported as UP/RUNNING solely from repository state:

- local WSL process liveness
- browser/extension liveness
- bridge listener liveness
- scheduler/timer liveness
- runtime-exchange polling liveness
- current scout/watcher process liveness

These remain `UNVERIFIED` until fresh runtime evidence exists (for example a bounded health/PING attestation, scheduler-produced request, matched exchange response, or fresh lifecycle transition produced by the local runtime).

## Unattended-operation dependency

Unattended operation still requires the laptop, WSL, browser and the armed project tab/runtime path to remain available. Repository PASS means the tested code path is present; it is not a live-process attestation.
