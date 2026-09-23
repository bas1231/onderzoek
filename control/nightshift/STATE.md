# Prediction Nightshift State

Timestamp: 2026-09-23 22:xx CEST
Lane: A — bridge/delivery + wake-loop continuity

## Completed
1. Server-side stale-result/SENT regression suite.
Commit: `8e7e4e68fcf2cf22619e09e71bb12b875aaffb8e`
File: `control/tampermonkey_multichat/test_bridge_server_sent_semantics.py`
Covers SENT exclusion, OUTBOX eligibility, first ACK move, repeated ACK idempotence and no restoration to OUTBOX.

2. Dedicated wake-only userscript send fix.
Commit: `b39cfb1fa5db22c6ee21173631387888cdc8c65d`
File: `control/tampermonkey_multichat/prediction-nightshift-wake.user.js`
Version: `0.1.1`
Browser runtime verification remains pending.

3. This wake: added focused browser-side delivery dedupe/restart static regression coverage without modifying the stale canonical v0.3.3 userscript.
Commit: `b7750a7173221ac8e5a1ca3d21a023827d41520d`
File: `control/tampermonkey_multichat/test_userscript_delivery_dedupe_static.py`

Coverage:
- sent-event memory is persistent Tampermonkey GM storage;
- an already remembered event is ACKed and skipped, never resubmitted;
- a newly submitted event is remembered before ACK, preventing resend after ACK transport failure;
- `restartWakeLoop()` does not clear sent-event memory.

## Evidence / tests
- Canonical userscript source confirms `KEY_SENT_EVENTS = prediction_sent_events_v3`, persistent `GM_getValue`/`GM_setValue`, remembered-event ACK+continue, remember-before-ACK ordering, and no sent-memory reset on wake-loop restart.
- Source inspection confirms server discovery enumerates OUTBOX and ACK moves OUTBOX→SENT.
- GitHub connector cannot execute WSL/Chrome/Tampermonkey runtime, so no local/browser UP/RUNNING claim is made.
- New static test and prior server regression test are committed but runtime execution is `UNVERIFIED` here.

Later runtime-capable verification:
`python3 -m unittest control/tampermonkey_multichat/test_bridge_server_sent_semantics.py -v`
`python3 -m unittest control/tampermonkey_multichat/test_userscript_delivery_dedupe_static.py -v`

## Current status
- Server-side SENT→no-redelivery: `SOURCE_CONFIRMED`; regression committed; execution `UNVERIFIED`.
- Browser event-id duplicate/stale replay protection: `SOURCE_CONFIRMED`; static regression committed; execution `UNVERIFIED`.
- Dedicated nightshift wake v0.1.1: `PATCHED`; live browser verification pending.
- Canonical Prediction Chat Wake Bridge remains v0.3.3 while local/browser code advanced separately; do not overwrite blindly.
- Task-level duplicate suppression across differently identified RESULT_READY events: `NOT YET PROVEN`.
- Local runtime UP/RUNNING: `UNVERIFIED`.

## Blocker
The repository does not contain the locally advanced v0.4.5/v0.4.6 userscript state, so safe canonical convergence cannot be done from GitHub alone without overwrite/regression risk.

## Next exact step
Inspect available v0.4.x patch/checkpoint artifacts for RESULT_READY task identity and add one narrowly scoped task-level duplicate-suppression guard/test compatible with the advanced local script. Do not overwrite the canonical userscript until the patch chain is reconciled.

Safety: no live trading, no wallet/fund movement, no paid actions, no credentials, no security misuse. Economic state remains `NO_PROVEN_EDGE`.
