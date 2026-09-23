# Prediction bridge checkpoint — 2026-09-23

Status: **PAUSED**

## Current local line

The local/browser line has been advanced through **v0.4.3**. Do not reconstruct or overwrite the local userscript from the older `main` userscript until the exact local v0.4.3 file has been intentionally promoted.

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
- v0.4.3 changes only the final ChatGPT composer/send hop to a ProseMirror-aware fill + enabled Send click + visible-new-user-turn proof before ACK.
- Task `BRIDGE-PING-20260923-ASSIST-6D91F2A8C4B7` returned with exact task ID, `Action: BRIDGE_PING`, exit code 0 and `BRIDGE_PONG` in the originating session: valid end-to-end PASS for that task.

A clean fresh-chat v0.4.3 proof was deliberately deferred when this work was paused.

## Reproducible patch chain saved in Git

Starting from the locally tested 0.3.x line:

1. `patch_v040_response_cycle_fixed2.py`
2. `patch_v041_send_confirm.py`
3. `patch_v042_enter_first.py`
4. `patch_v043_prosemirror_send.py`

Each patch creates a local backup before writing and should be followed by `node --check` and `install_multichat.sh`.

## Resume rule

When resuming this bridge work, first inspect the exact local userscript/version and browser status. Do **not** start again from the stale remote userscript or replay old task IDs. The next useful test is one clean new Prediction chat on v0.4.3 with a never-before-used `BRIDGE_PING` task ID.
