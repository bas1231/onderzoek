# Nachtwerkrapport — hourly timer recovery

Timestamp: 2026-09-24T07:35:00+02:00

## Finding
The canonical deployer copied only `prediction-research-hourly-director.service` into the user systemd directory, then enabled the timer by name without copying the canonical `.timer` unit. Therefore a missing or stale installed timer could survive while deployment still reported PASS. Historical `SYSTEMD-HOURLY-AUDIT-E136` is not evidence of a timer failure: its probe itself crashed on `dict.setitem`.

This is a concrete deployment defect consistent with the observation that runtime-exchange stopped producing hourly requests after 2026-09-23 14:00+02:00, while the scanner remained correctly wired inside `hourly_cycle.py`.

## Changes
- `control/jobs/deploy_hourly_runtime_sync_e001.py`: atomically install both canonical service and timer; daemon-reload; `enable --now`; verify installed timer contract; fail closed unless enabled+active.
- `tests/test_hourly_timer_deployer.py`: static regression guards for both-unit deployment and activation/verification.
- `control/tasks/pending/DEPLOY-HOURLY-TIMER-RECOVERY-E001.json`: bounded existing-control-plane recovery task. No commandmarker.
- commits: `93a5d0cf`, `9b952c2a`, `09a5b307`.

## Evidence / claims
- PASS: defect exists in prior deployer and remote-side repair is committed.
- PASS: recovery task is durably dispatched through the existing control-plane queue.
- UNVERIFIED: local task pickup/execution.
- UNVERIFIED: local systemd timer enabled/active after recovery.
- UNVERIFIED: next natural timer -> cycle -> market-instance scan -> exchange -> report -> Git checkpoint.
- No UP/RUNNING claim is made from Git state.

## End-state checklist
- bridge/result-delivery: PASS code/tests; live browser state UNVERIFIED.
- scheduler deployment contract: PASS remote code.
- scheduler live state: UNVERIFIED pending recovery result.
- runtime exchange: UNVERIFIED.
- scouts/recon/specialist/red-team/reproducer gates: PASS durable research-cycle evidence where applicable.
- reporting/Git persistence: PASS.
- health/recovery: PASS remote design; local execution UNVERIFIED.
- economic conclusion: NO_PROVEN_EDGE.

## Next exact step
Observe the existing control-plane task result. If it completes, require a fresh natural hourly receipt and market-instance-scan artifact before promoting scheduler/runtime-exchange liveness. If the task is not picked up, the remaining blocker is below the Git/control-plane layer and requires direct local systemd/bridge reachability evidence.
