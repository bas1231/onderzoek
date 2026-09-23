# Prediction bridge checkpoint — 2026-09-23

Status: **PAUSED / recovery patch prepared**

## Current local line

The local/browser line has been advanced through **v0.4.4** and a **v0.4.5 recovery patch** is now saved in Git. Do not reconstruct or overwrite the local userscript from the older `main` userscript until the exact local line has been intentionally promoted.

Canonical command protocol remains:

`[[PREDICTION_CMD:<ACTION>:<TASK_ID>]]`

For health tests use `BRIDGE_PING` with a genuinely new task ID.

## Proven infrastructure

The local three-service chain remained healthy during the work:

- 8765: `prediction-chat-wake`, multi-chat enabled;
- 8766: command receiver, active and intentionally unchanged;
- 8767: `prediction-chat-command-router`, forwarding to 8766.

Per-tab `chat_id`/`consumer_id` routing is operational. Command detection, routing to WSL, result creation and outbox routing have all been demonstrated.

## Diagnostic history

- v0.4.0 fixed the command side: newest assistant turn only, response stability, no global full-DOM observer, global task dedupe.
- v0.4.1 removed false ACKs: a wake event is not ACKed unless the result actually appears as a new ChatGPT user turn.
- Fresh v0.4.1 test `BRIDGE-PING-20260923T1808-4C8E1F7B92D54A61` produced a route + outbox item and correctly remained out of `sent` when browser submission failed.
- Fresh v0.4.2 test `BRIDGE-PING-20260923T1816-8F4C27D1A9B3` likewise produced route + outbox and no false `sent` transition.
- v0.4.3 changed only the final ChatGPT composer/send hop to a ProseMirror-aware fill + enabled Send click + visible-new-user-turn proof before ACK.
- v0.4.4 added native requestSubmit -> pointer/click -> Enter fallback while retaining the strict user-turn-before-ACK rule.
- Task `BRIDGE-PING-20260923-ASSIST-6D91F2A8C4B7` returned with exact task ID, `Action: BRIDGE_PING`, exit code 0 and `BRIDGE_PONG` in the originating session: valid end-to-end PASS for that task.
- DEV capability probe `DEV-PRED-BRIDGE-CAPABILITY-PROBE-E001` executed successfully in `prediction_research_prod`, proving the guarded async DEV route works end-to-end.

## Proven v0.4.4 failure mode

A large `RESULT_READY` payload for `DEV-PRED-BRIDGE-CAPABILITY-PROBE-E001` was visibly submitted to ChatGPT multiple times.

Root cause: the browser confirmation logic required the number of visible user-message DOM nodes to increase. In a long/virtualized ChatGPT conversation the browser can prune/virtualize older turns, so the visible count can remain constant even though a new user turn was actually created. The send therefore succeeded but the bridge falsely classified it as unconfirmed, did not ACK the wake event, and resubmitted the same result.

## v0.4.5 recovery patch

Saved as:

`control/tampermonkey_multichat/patch_v045_delivery_dedupe.py`

The patch makes result delivery idempotent by:

1. matching a short unique `RESULT_READY: <task_id>` anchor rather than the full large payload;
2. comparing newest user-turn identity/fingerprint instead of relying on visible node-count growth;
3. scanning recent user turns before a retry and ACKing an already-visible result instead of resending it;
4. remembering delivered task IDs in addition to event IDs, so duplicate outbox events for one completed task are drained without another ChatGPT message;
5. running one recovery scan after an apparently unconfirmed submit before permitting any retry.

This keeps the strict safety boundary: no generic shell, no live trading, no paid actions, no wallets, and no new network capability.

## Reproducible patch chain saved in Git

Starting from the locally tested 0.3.x line:

1. `patch_v040_response_cycle_fixed2.py`
2. `patch_v041_send_confirm.py`
3. `patch_v042_enter_first.py`
4. `patch_v043_prosemirror_send.py`
5. `patch_v044_autosubmit.py`
6. `patch_v045_delivery_dedupe.py`

Each patch creates a local backup before writing and should be followed by `node --check` and `install_multichat.sh`.

## Resume rule

Keep the Tampermonkey bridge disabled while applying v0.4.5. After install/reload, use one fresh `BRIDGE_PING` with a never-before-used task ID. Do not reuse the DEV capability-probe task ID. The first startup should also drain the already-visible stuck `DEV-PRED-BRIDGE-CAPABILITY-PROBE-E001` event without posting it again.
