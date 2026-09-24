# Nachtwerkrapport — 2026-09-24 07:32 CEST

Economic default: `NO_PROVEN_EDGE`.

## Scope
Inspected latest `main` after the scheduler/cycle-correlation work. The newest bridge commits had introduced an opt-in server heartbeat that writes a user-visible `ga door` commandmarker into the routed chat. That conflicts with the control-plane requirement that automatic commandmarkers are not a normal scheduler mechanism and should not be emitted unless explicitly necessary.

## Changes
- `86264bc9` — `control/tampermonkey_multichat/nightshift_server_heartbeat.py`
  - heartbeat activation now fails closed unless `--allow-commandmarker` is supplied explicitly;
  - persisted mode records `allow_commandmarker: true` only after that explicit opt-in;
  - status exposes whether explicit opt-in is present;
  - old callers that merely run `enable <task>` can no longer silently create new commandmarkers.
- `704ced27` — `tests/bridge/test_nightshift_commandmarker_optin.py`
  - regression contract pins the explicit opt-in requirement;
  - also pins that the heartbeat remains expiry-bounded and cannot claim `RUNNING` liveness.

## Tests
Regression test source was added on `main`. This automation cannot execute the local WSL/browser test suite, so execution result is `UNVERIFIED`; no PASS is inferred from committing test code.

## Runtime evidence
No fresh local WSL/systemd/browser runtime attestation was established in this run. Recent Git commits are code-state evidence only. Local scheduler, bridge and runtime-exchange liveness remain `UNVERIFIED`.

## End-state checklist
- Bridge server-side SENT/task dedupe: `PASS_CODE_TEST_CONTRACT / UNVERIFIED_LIVE`
- Browser stale/in-memory/task-level/restart dedupe: `PASS_CODE_TEST_CONTRACT / UNVERIFIED_LIVE`
- Automatic commandmarker safety: `PASS_FUTURE_ACTIVATION_GUARD / LEGACY_ACTIVE_MODE_UNVERIFIED`
- Scheduler wrapper/cooldown/fail-closed: `PASS_CODE_TEST_CONTRACT / UNVERIFIED_LIVE`
- Runtime exchange: `UNVERIFIED_LIVE`
- Scouts: `PASS_DURABLE_RESEARCH_CYCLE`
- Recon: `PASS_DURABLE_RESEARCH_CYCLE`
- Specialist dispatch: `PASS_DURABLE_RESEARCH_CYCLE`
- Red-team/reproducer gate: `PASS_DURABLE_RESEARCH_CYCLE`
- Reporting: `PASS`
- Git persistence: `PASS`
- Health/recovery: `PASS_CODE_TEST_CONTRACT / UNVERIFIED_LIVE`
- Natural timer -> cycle -> exchange -> report -> Git correlation: `UNVERIFIED_LIVE`

## Blockers
1. Existing local `nightshift_mode.json`, if already enabled before this commit, cannot be inspected or disabled from GitHub; it is bounded by expiry but its exact current state is unknown.
2. Fresh local runtime evidence is still required before any `UP/RUNNING` claim.

## Exact next step
On the next remotely observable local cycle, consume the correlated scheduled-cycle/health receipt and verify timer -> canonical run_id -> exchange state -> report -> Git checkpoint. Do not use heartbeat/commandmarker traffic as liveness proof.
