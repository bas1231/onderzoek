# Nightwork reliability audit — 2026-09-24 00:18 Europe/Amsterdam

## Scope

Priority order followed: bridge/result delivery first, then scheduler/runtime-exchange observability. No live trading, paid action, wallet action, credential write, post-close leakage, or OpenAI API action was performed.

## Git state inspected

- `control/browser_bridge_core.py`
- `control/browser_extension/content.js`
- `control/RELIABILITY_STATUS.md`
- `tests/bridge/`
- latest `main` commits through `b3f4e29c226d5d11a35ef498dbd3805420985cc5`
- `control/hourly/` inventory

## Meaningful finding

The browser result path already persists pending ACKs in `chrome.storage.local`, retries ACKs with backoff, and the server reconciles durable lifecycle `ACKED` state. This is good crash/restart groundwork. However, the current browser poll path does not yet have a proven pre-send suppression gate for the case where the same `/outbox` item is returned while that task already exists in the durable pending-ACK queue. Therefore duplicate `RESULT_READY`/result-message replay cannot yet be declared closed from repository inspection alone.

Server-side `next_outbox_item()` skips durable ACKED tasks and recovers ACK state from the lifecycle ledger. It marks a result `DELIVERED` when exposed, not when browser send is durably acknowledged. That distinction is intentional for retryability but means browser-side sent/pending-ACK dedupe remains a required gate.

## Change in this run

`control/RELIABILITY_STATUS.md` was corrected so repository/test PASS is no longer presented as proof that local WSL, bridge, browser, scheduler, exchange poller, or scouts are live. Overall live status is now `UNVERIFIED_LIVE` until fresh runtime evidence exists.

## Tests/evidence

Static inspection: PASS for presence of durable browser task queue, durable result ACK queue, ACK retry/backoff, lifecycle ACK reconciliation, idempotent enqueue, bounded processed-task history, and health endpoint.

Dynamic local runtime test: UNVERIFIED — this automation has no direct process/socket access to the user's WSL/browser runtime.

Full automatic research cycle after this audit: UNVERIFIED in this run. Recent Git history contains later research commits, but a Git commit alone is not treated as proof of current local liveness.

## End-state checklist

| Component | State | Evidence / blocker |
|---|---|---|
| Bridge server result ACK filtering | PASS | ACKED tasks skipped; lifecycle ACK reconciliation present |
| Browser duplicate result delivery | FAIL | pending-ACK persistence exists, but pre-send suppression for an already-pending task is not yet proven |
| Browser stale task replay | PASS (static) | durable processed IDs + in-flight set + idempotent server enqueue |
| Bridge live process | UNVERIFIED | needs fresh bounded health/PING runtime evidence |
| Scheduler | UNVERIFIED | repository presence is not process/timer liveness |
| Runtime exchange | UNVERIFIED | needs fresh scheduler request + matched response evidence |
| Scouts | UNVERIFIED live | definitions/state exist; process liveness not attested here |
| Recon | UNVERIFIED live | same |
| Specialist dispatch | UNVERIFIED live | same |
| Red-team/reproducer gate | PASS (design/static) | gated architecture present; no live invocation attested here |
| Reporting | PASS (Git persistence) | durable reports/commits exist |
| Git persistence | PASS | this report and reliability correction committed to `main` |
| Health/recovery | PASS (static), UNVERIFIED live | health/ACK/recovery paths present; fresh runtime attestation absent |

## Blockers

1. Browser result replay closure still needs a code-level pre-send gate: when `resultAckPending(task_id)` is true, retry/flush ACK and do not reinsert/re-send the result message.
2. Fresh local liveness cannot be inferred remotely. After code closure, the smallest valid proof is a bounded PING/health canary plus one scheduler-produced request/response lifecycle; do not use a large capability probe.

## Exact next step

Patch the existing browser result-delivery path (do not add a subsystem) so a task already present in `predictionPendingResultAcksV1` is never sent again. Add a regression test that requires this pre-send check. Then obtain/consume the next naturally produced runtime evidence; only if that remains absent should one bounded local PING be requested.

Economic conclusion remains `NO_PROVEN_EDGE`.
