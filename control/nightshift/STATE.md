# Prediction Nightshift State

Timestamp: 2026-09-23 22:xx CEST
Lane: A — bridge/delivery + wake-loop continuity

## Completed
1. Added a standard-library regression suite for `control/tampermonkey_multichat/bridge_server_v2.py` covering the exact stale-result failure class seen tonight.

Commit: `8e7e4e68fcf2cf22619e09e71bb12b875aaffb8e`

New test file:
- `control/tampermonkey_multichat/test_bridge_server_sent_semantics.py`

Coverage added:
- an event present only in `sent/` is never eligible via `oldest_event()`;
- an event in `outbox/` is eligible before ACK;
- first `/ack` moves the event from `outbox/` to `sent/`;
- a repeated `/ack` returns success with `already_acked=true`;
- repeated ACK never restores the event to `outbox/` and it remains ineligible for delivery.

2. Fixed the dedicated wake-only userscript after browser evidence showed it filled the ChatGPT composer but did not submit.

Commit: `b39cfb1fa5db22c6ee21173631387888cdc8c65d`
File: `control/tampermonkey_multichat/prediction-nightshift-wake.user.js`
Version: `0.1.1`

Changes:
- added current ChatGPT `#composer-submit-button` selector;
- added browser-native `requestSubmit` path;
- added real pointer/mouse activation sequence;
- added Enter fallback;
- added send confirmation via new user turn / cleared composer;
- failed send no longer deadlocks because exact wake text may be retried after an 8s cooldown;
- arbitrary user-typed composer text is never overwritten;
- successful wake timestamp is recorded only after confirmed submission.

## Evidence / tests
- Source inspection confirms current server discovery enumerates only `OUTBOX` through `event_files()` and ACK uses `os.replace(src, dst)` from OUTBOX to SENT.
- Browser screenshot from the user confirmed v0.1.0 had filled the exact wake text while leaving the blue send button unsent; this directly motivated the selector/activation/retry fix.
- GitHub connector cannot execute the user's Chrome/Tampermonkey runtime, so browser-side v0.1.1 remains `USER_RUNTIME_VERIFICATION_REQUIRED` until the next automatic wake is observed.
- Server regression test remains locally unexecuted from this environment.

Local verification command for server test:
`python3 -m unittest control/tampermonkey_multichat/test_bridge_server_sent_semantics.py -v`

## Current status
- Server-side SENT→no-redelivery invariant: `SOURCE_CONFIRMED`, regression coverage committed, local execution `UNVERIFIED`.
- Dedicated nightshift wake script v0.1.1: `PATCHED`, live browser verification pending.
- Browser-side duplicate/stale replay protection in the old Prediction Chat Wake Bridge: `NOT YET PROVEN`.
- Canonical GitHub main Prediction Chat Wake Bridge remains stale at v0.3.3 while local/browser code has been advanced separately; convergence risk remains.
- Local runtime UP/RUNNING: `UNVERIFIED` from GitHub-only work.

## Next exact step
After v0.1.1 is installed in Tampermonkey and one automatic wake is confirmed, inspect the v0.4.5/v0.4.6 bridge patch chain and converge browser-side result delivery to one canonical restart-safe implementation without overwriting the user's locally advanced script. Add focused regression/static coverage for task-level duplicate suppression.

Safety: no live trading, no wallet/fund movement, no paid actions, no credentials, no security misuse. Economic state remains `NO_PROVEN_EDGE`.
