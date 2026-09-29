# Prediction Command Bus — Current State

Updated: 2026-09-29
Infrastructure track: `TIERA-BRIDGE-COMMAND-BUS-20260929-E001`
Session-bootstrap build: `TIERA-SESSION-BOOTSTRAP-20260929-E001`
Intelligence tier: A
Implementation model: GPT-5.6 Sol
Actual reasoning level: `UNAVAILABLE_TO_RUNTIME`
Formal qualification: `REQUIRES_HIGH_INTELLIGENCE_REVIEW`

## Current operational status

The local command bus is installed and operational. The terminal-safe installer preserved the hardened wake wrapper, installed the read-only GitHub poller and activated the systemd timer. The command path is:

`ChatGPT assistant -> private GitHub command file -> read-only WSL poller -> localhost router/receiver -> WSL execution -> wake bridge -> same ChatGPT session route`

The capability-scoped project executor is operational for ordinary Prediction build/test/diagnose/user-level management work inside its documented guardrails.

## Proven command-bus baseline

Successful end-to-end evidence on 2026-09-29:

- `BRIDGE-BUS-AUTO-20260929-E001` -> PASS, exit 0
- `TM-PING-1790690332005` -> PASS, exit 0, returned to the intended chat
- `BRIDGE-COMMAND-BUS-CURRENT-ROUTE-E008` -> PASS, exit 0, returned to that same chat through an explicit session route
- `DEV-PRED-SESSION-BOOTSTRAP-INSTALL-20260929-E010` -> PASS, exit 0, installed and runtime-verified automatic session bootstrap
- `DEV-PRED-STATUS-COMPACTION-FIX-20260929-E013` -> PASS, exit 0, installed and runtime-verified nested-status-safe result compaction

This proves the primary GitHub command-bus path once a valid same-chat route exists, plus the installed automatic-bootstrap runtime and corrected DEV result-status compactor.

The main legacy result-path failure found earlier was head-of-line blocking. The installed result queue uses fail-closed `outbox -> inflight -> sent` semantics; ambiguous `inflight` delivery is not silently treated as sent or automatically replayed.

## Multi-session routing incident

A later test exposed a separate addressing problem: a command could execute correctly while its result was routed to an older/global pinned ChatGPT route instead of the session that issued it.

The explicit per-command `route_task_id` rule fixed normal multi-session command delivery once the current chat had a known route. However, the original new-chat bootstrap procedure still depended on a legacy visible DOM marker or manual menu ping. That was an incomplete solution because the legacy assistant-DOM command scanner had already proven unreliable.

## Automatic new-session bootstrap — installed

Task:

`DEV-PRED-SESSION-BOOTSTRAP-INSTALL-20260929-E010`

Observed result in the controlling chat:

`NIGHTSHIFT_WSL_RESULT_V1 task=DEV-PRED-SESSION-BOOTSTRAP-INSTALL-20260929-E010 status=PASS exit=0 rcs=1:0 head=529896aaae12b3be4e1f13ec1ae177a781410605 event=1790693622-48084ad6d046`

E010 performed the following before returning PASS:

1. ran the deterministic session-bootstrap regression suite;
2. ran compile checks for the new wrapper and hardened bridge module;
3. installed the hardened bridge module to the allowlisted Prediction runtime;
4. installed `bridge_server_session_bootstrap.py` as the active `bridge_server.py` runtime;
5. restarted `prediction-chat-wake.service`;
6. required the service to be active;
7. imported the installed runtime and required `Handler.server_version == "PredictionChatWake/0.9-session-bootstrap"`;
8. ran an installed-runtime canary that created a `SESSION-ROUTE-*` route and corresponding PASS announcement.

Canonical implementation:

`control/tampermonkey_multichat/bridge_server_session_bootstrap.py`

The wrapper uses the already-existing wake `/next` poll. Current Prediction browser tabs already send a stable `chat_id` plus `consumer_id` when polling for results. For a chat without a previously proven routed result, the wake server now creates a deterministic chat-scoped route and an idempotent announcement:

`NIGHTSHIFT_WSL_RESULT_V1 task=SESSION-ROUTE-... status=PASS exit=0 kind=SESSION_ROUTE_BOOTSTRAP`

After that result is ACKed in the same chat, the `SESSION-ROUTE-*` task ID is the canonical `route_task_id` for GitHub command-bus work from that session.

The normal new-session procedure therefore no longer requires the assistant to emit a visible `[[PREDICTION_CMD:...]]` marker. Legacy/menu PING remains diagnostic fallback only.

## Result compaction incident — fixed and installed

A follow-up diagnostic exposed a browser-facing status compaction bug. Task `DEV-PRED-ROUTE-BOOTSTRAP-DIAG-20260929-E011` returned the contradictory summary:

`status=FAIL exit=0 rcs=1:2,1:0 error=TaskError`

E011 intentionally printed the stored receipt of the older failed E009 task. The outer DEV runner then completed its own command with RC 0 and printed its final `DEV_TASK_STATUS=PASS`. The old hardened compactor selected the first embedded `DEV_TASK_STATUS`, first `ERROR_CLASS`, and historical `COMMAND_n_RC` markers from raw output, so an embedded historical failure could incorrectly flip the browser summary of a successful diagnostic to FAIL.

The fix was installed by:

`DEV-PRED-STATUS-COMPACTION-FIX-20260929-E013`

Observed result in the controlling chat:

`NIGHTSHIFT_WSL_RESULT_V1 task=DEV-PRED-STATUS-COMPACTION-FIX-20260929-E013 status=PASS exit=0 rcs=1:0 head=a43ad4a2a3014e36ec1932b4b4b31b7fd269f140 event=1790695022-7d3aaf3f690e`

E013 ran the nested-status regression test and compile checks, installed `bridge_server_status_compaction.py` as the active wake runtime, restarted and required `prediction-chat-wake.service` active, and executed a runtime assertion requiring the outer PASS to remain authoritative even when an embedded older receipt contains FAIL/TaskError/RC=2.

Canonical implementation:

- `control/tampermonkey_multichat/bridge_server_status_compaction.py`
- `control/tampermonkey_multichat/test_status_compaction_nested.py`

This incident was a result-summary/reporting defect; it did not invalidate E010 or prove a command-bus/session-bootstrap execution failure.

## Remaining acceptance gate for automatic bootstrap

E010 proves implementation, deterministic behaviour, installation, service restart, service liveness and installed-runtime canary. E013 proves the corrected result-status compactor is installed and runtime-verified.

The remaining product-level acceptance test is external to the current already-routed chat: open a genuinely brand-new Prediction ChatGPT chat and verify that, after it has a stable ChatGPT conversation URL and the existing wake userscript is running, it automatically receives its own:

`SESSION-ROUTE-* ... status=PASS exit=0 kind=SESSION_ROUTE_BOOTSTRAP`

without an assistant DOM marker and without a manual menu ping.

Once observed, record that exact task ID/result here as the final same-chat automatic-bootstrap proof. Until then, do not claim that brand-new-chat product behaviour has been independently observed even though the runtime installation/canary is PASS.

## Project executor operational proof

Successful evidence:

- `DEV-PRED-PROJECT-EXEC-INSTALL-E002` — compile + deterministic unittest suite PASS;
- `DEV-PRED-PROJECT-EXEC-CANARY-E001` — isolated worktree, repository-owned Python write/execute and local Git inspection PASS;
- `DEV-PRED-PROJECT-EXEC-OPS-E003` — Python execution, isolated local Git commit, bounded runtime install, `prediction-*` user-service inspection and Prediction journal-read path PASS.

The executor uses a repository-local Git identity in its isolated worktrees and does not mutate the user's global Git identity.

## Canonical routing rule

See `control/bridge_commands/SESSION_ROUTING.md`.

In summary:

- each active Prediction chat uses its own explicit same-chat route;
- brand-new chats are now expected to receive an automatic `SESSION-ROUTE-*` bootstrap from the wake server;
- after that PASS, use the route task explicitly on every normal command from that chat;
- do not normally use `route_task_id:null` when multiple sessions may exist;
- `DISPATCHED` is not successful same-chat delivery;
- command task IDs are immutable and at-most-once; never reuse a claimed command to repair delivery.

## Canonical implementation/docs

- `00_CHATGPT_START_HERE.md` — mandatory first read.
- `control/bridge_commands/SESSION_ROUTING.md` — per-session routing and automatic bootstrap.
- `control/bridge_commands/OPERATIONS.md` — command-bus operations.
- `control/NEW_SESSION_LOCAL_EXECUTION.md` — project execution flow.
- `control/PROJECT_EXECUTOR.md` — executor capabilities/guardrails.
- `control/tampermonkey_multichat/PROTOCOL.md` — bridge protocol.
- `control/tampermonkey_multichat/bridge_server_session_bootstrap.py` — automatic bootstrap wrapper.
- `control/tampermonkey_multichat/test_session_route_bootstrap.py` — regression suite.
- `control/tampermonkey_multichat/bridge_server_status_compaction.py` — installed nested-receipt-safe result compactor.
- `control/tampermonkey_multichat/test_status_compaction_nested.py` — regression suite for result status parsing.
- `control/bridge_commands/COMMAND_SCHEMA_V1.json` — immutable command schema.
- `control/bridge_commands/command_bus_poller.py` — read-only GitHub poller with durable command claims.

## Guardrails

Unchanged:

- WSL side is GitHub read-only: no autonomous push/publication;
- no live trading;
- no paid action without the separately required exact approval;
- no wallet/crypto action;
- no credential reads/writes;
- no unrestricted root/sudo;
- no unrestricted external networking from project code;
- command claims are durable before localhost dispatch;
- ambiguous command dispatches are never automatically retried;
- ambiguous result delivery remains fail-closed;
- production working tree is not the command-bus fetch target.

## Qualification gate

The command bus, explicit session routing, project executor, automatic session-bootstrap runtime and corrected result compactor are operationally implemented and have passed their documented local/runtime tests. Formal independent Tier-A qualification remains `REQUIRES_HIGH_INTELLIGENCE_REVIEW`. Operational evidence must not be used to relax trading, cost, wallet, credential, provenance or autonomy guardrails.
