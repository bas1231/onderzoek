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
Live browser send was subsequently observed working by the user.

3. Browser-side delivery dedupe/restart static regression coverage.
Commit: `b7750a7173221ac8e5a1ca3d21a023827d41520d`
File: `control/tampermonkey_multichat/test_userscript_delivery_dedupe_static.py`

Coverage:
- sent-event memory is persistent Tampermonkey GM storage;
- an already remembered event is ACKed and skipped, never resubmitted;
- a newly submitted event is remembered before ACK, preventing resend after ACK transport failure;
- `restartWakeLoop()` does not clear sent-event memory.

4. Short continuation wake.
Commit: `d70bf0b4fc8dc70c6535a29b55713c4d7281746c`
File: `control/tampermonkey_multichat/prediction-nightshift-wake.user.js`
Version: `0.1.2`
Change: wake message is now simply `ga door`; the loop resumes shortly after a completed assistant turn instead of waiting for a guessed ChatGPT timeout. OpenAI Help documentation checked on 2026-09-23 does not publish an exact regular-chat inactivity/generation timeout; the public troubleshooting guidance only suggests waiting 30–60 seconds when a response appears stuck, which is not a timeout contract.

## Evidence / tests
- Canonical userscript source confirms `KEY_SENT_EVENTS = prediction_sent_events_v3`, persistent `GM_getValue`/`GM_setValue`, remembered-event ACK+continue, remember-before-ACK ordering, and no sent-memory reset on wake-loop restart.
- Source inspection confirms server discovery enumerates OUTBOX and ACK moves OUTBOX→SENT.
- GitHub connector cannot execute WSL/Chrome/Tampermonkey runtime, so local WSL service state remains unverified here.
- Static/browser tests are committed but local execution still needs a runtime-capable path.

Later runtime-capable verification:
`python3 -m unittest control/tampermonkey_multichat/test_bridge_server_sent_semantics.py -v`
`python3 -m unittest control/tampermonkey_multichat/test_userscript_delivery_dedupe_static.py -v`

## Current status
- Wake-loop send path: `LIVE_OBSERVED_WORKING` on v0.1.1; v0.1.2 short-message change committed, browser install pending.
- Server-side SENT→no-redelivery: `SOURCE_CONFIRMED`; regression committed; execution `UNVERIFIED`.
- Browser event-id duplicate/stale replay protection: `SOURCE_CONFIRMED`; static regression committed; execution `UNVERIFIED`.
- Canonical Prediction Chat Wake Bridge remains v0.3.3 while local/browser code advanced separately; do not overwrite blindly.
- Task-level duplicate suppression across differently identified RESULT_READY events: `NOT YET PROVEN`.
- WSL control from the nightshift: `NOT CONNECTED`; this is now the top blocker.
- Local runtime UP/RUNNING: `UNVERIFIED`.

## Design decision
Do not wait for an undocumented ChatGPT timeout. A normal chat turn is already over when the assistant response completes, so the wake loop should trigger the next turn soon after completion. Keep the wake transport separate from WSL control/result transport.

For WSL control, reuse the existing allowlisted localhost command infrastructure rather than inventing generic shell access. The nightshift transport must:
- send only allowlisted task IDs/actions;
- use persistent task-level dedupe;
- never place unbounded WSL stdout/diffs in the composer;
- hard-cap and summarize returned results;
- ACK only after a compact result is visibly delivered;
- preserve fail-closed behavior and no live trading/funds/credentials.

## Next exact step
Build the dedicated Nightshift WSL control path on top of the existing localhost allowlisted command/router infrastructure, with bounded result compaction and no raw RESULT_READY dump delivery. Then use it first for a tiny BRIDGE_PING/local unittest canary before any broader runtime work.

Safety: no live trading, no wallet/fund movement, no paid actions, no credentials, no security misuse. Economic state remains `NO_PROVEN_EDGE`.
