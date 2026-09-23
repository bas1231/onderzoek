# Prediction Nightshift State

Timestamp: 2026-09-23 late evening CEST
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

4. Short continuation wake.
Commit: `d70bf0b4fc8dc70c6535a29b55713c4d7281746c`
Version: `0.1.2`
Wake text reduced to `ga door` and resumed shortly after completed assistant turns.

5. Dedicated bounded Nightshift WSL control integrated into `Prediction Nightshift Wake`.
Version: `0.2.0`
The userscript now uses Tampermonkey `GM_xmlhttpRequest` to the existing localhost command/router (`8767`) and result server (`8765`), accepts only `SIX_AI_HEALTH` plus `DEV-PRED-NIGHTSHIFT-*` task IDs, persists command dedupe, compacts WSL results to <=900 characters, ACKs the outbox event, and submits only the compact summary. Raw WSL stdout/diffs are never posted into the ChatGPT composer.

6. First bounded WSL canary manifest created.
Repo: `bas1231/fg-assistent`
Commit: `a7a8d4a2758cd446fdb51249c9c5c7fcf1e7f175`
Task: `DEV-PRED-NIGHTSHIFT-BRIDGE-CANARY-E001`
It syncs only the server semantics regression test, runs that unittest in `prediction_research_prod`, then reports `git rev-parse HEAD`. No generic shell, live trading, paid actions, credentials or device/network actions are enabled.

## Evidence / tests
- Canonical nightshift userscript is v0.2.0 and contains bounded WSL control plus compact-result delivery.
- Existing bridge server source enumerates only OUTBOX for `/next`; ACK moves OUTBOX to SENT and repeated ACK is idempotent.
- Existing dev-task runner allowlists projects/commands and blocks live trading, paid actions, network devices, generic shells and non-loopback network references.
- Browser wake send has been live-observed working; v0.2.0 WSL round-trip is now the next canary.

## Current status
- Wake-loop send path: `LIVE_OBSERVED_WORKING`.
- Nightshift WSL-control code: `IMPLEMENTED`, live round-trip `PENDING CANARY`.
- Server-side SENT->no-redelivery: `SOURCE_CONFIRMED`; regression committed.
- Raw-result dump prevention in nightshift path: `SOURCE_CONFIRMED` by hard compaction and <=900-char composer payload.
- Local runtime UP/RUNNING: `UNVERIFIED` until canary result returns.

## Next exact step
Dispatch `DEV-PRED-NIGHTSHIFT-BRIDGE-CANARY-E001` through the v0.2.0 nightshift bridge and require a compact `NIGHTSHIFT_WSL_RESULT_V1` response. If PASS, immediately move to scheduler/runtime/service health. If FAIL, use only the compact status to fix the single failing layer.

Safety: no live trading, no wallet/fund movement, no paid actions, no credentials in Git, no security misuse. Economic state remains `NO_PROVEN_EDGE`.
