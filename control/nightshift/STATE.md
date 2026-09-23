# Prediction Nightshift State

Timestamp: 2026-09-23 22:xx CEST
Lane: A — bridge/delivery

## Completed this wake
Added a standard-library regression suite for `control/tampermonkey_multichat/bridge_server_v2.py` covering the exact stale-result failure class seen tonight.

Commit: `8e7e4e68fcf2cf22619e09e71bb12b875aaffb8e`

New test file:
- `control/tampermonkey_multichat/test_bridge_server_sent_semantics.py`

Coverage added:
1. an event present only in `sent/` is never eligible via `oldest_event()`;
2. an event in `outbox/` is eligible before ACK;
3. first `/ack` moves the event from `outbox/` to `sent/`;
4. a repeated `/ack` returns success with `already_acked=true`;
5. repeated ACK never restores the event to `outbox/` and it remains ineligible for delivery.

## Evidence / tests
- Source inspection confirms current server discovery enumerates only `OUTBOX` through `event_files()` and ACK uses `os.replace(src, dst)` from OUTBOX to SENT.
- The regression test is dependency-free and designed to run directly against the checked-out server module using a temporary filesystem and loopback HTTP server.
- GitHub connector cannot execute the local WSL checkout, so this wake does **not** claim the new test has run locally yet.

Local verification command for a later runtime-capable step:
`python3 -m unittest control/tampermonkey_multichat/test_bridge_server_sent_semantics.py -v`

## Current status
- Server-side SENT→no-redelivery invariant: `SOURCE_CONFIRMED`, regression coverage committed, local execution `UNVERIFIED`.
- Browser-side duplicate/stale replay protection: `NOT YET PROVEN`.
- Canonical GitHub userscript is still stale at v0.3.3 while local/browser code has been advanced separately; this is a convergence risk and must not be overwritten blindly.
- Local runtime UP/RUNNING: `UNVERIFIED` from this wake.

## Next exact step
Inspect the v0.4.5/v0.4.6 patch chain and make the browser-side delivery logic converge to one canonical, restart-safe implementation without overwriting the user's locally advanced script. Add a focused regression/static check for task-level duplicate suppression before declaring bridge delivery green.

Safety: no live trading, no wallet/fund movement, no paid actions, no credentials, no security misuse. Economic state remains `NO_PROVEN_EDGE`.
