# Prediction local execution architecture

Updated: 2026-09-29
Status: canonical technical overview
Formal qualification: `REQUIRES_HIGH_INTELLIGENCE_REVIEW`

## Purpose

This document gives one complete technical view of how a ChatGPT Prediction session sends bounded work to local WSL, how code is executed, how results return to the same chat, and where the safety boundaries live.

It does not replace the detailed operating documents. Those remain authoritative for their specific areas:

- `00_CHATGPT_START_HERE.md`
- `control/bridge_commands/CURRENT_STATE.md`
- `control/bridge_commands/SESSION_ROUTING.md`
- `control/NEW_SESSION_LOCAL_EXECUTION.md`
- `control/PROJECT_EXECUTOR.md`
- `control/bridge_commands/OPERATIONS.md`
- `control/tampermonkey_multichat/PROTOCOL.md`
- `control/tampermonkey_multichat/CHATGPT_PROJECT_INSTRUCTIONS.md`

When this overview conflicts with one of those current documents, the more specific current document wins.

## End-to-end architecture

Normal project execution follows this path:

`ChatGPT session`
`-> GitHub connector write into private repo bas1231/onderzoek`
`-> immutable command file in control/bridge_commands/inbox/`
`-> read-only WSL GitHub poller`
`-> localhost command router on 127.0.0.1:8767`
`-> local receiver on 127.0.0.1:8766`
`-> DEV transport adapter`
`-> capability-scoped project_task_executor.py`
`-> isolated WSL worktree / approved local runtime operation`
`-> DEV result`
`-> wake/result bridge on 127.0.0.1:8765`
`-> fail-closed result queue`
`-> browser /next poll`
`-> the originating ChatGPT session`

The two important architectural separations are:

1. **The command bus is transport.** It moves an immutable task from ChatGPT/GitHub into WSL and routes the result back.
2. **The project executor is authority.** It decides which local capabilities and operations are allowed for the task and prevents the command bus from becoming an unrestricted shell.

## Repository roles

### `bas1231/onderzoek`

This repository is the canonical control-plane repository for Prediction local execution.

Important paths:

- `control/bridge_commands/inbox/<TASK_ID>.json` — immutable command-bus task.
- `control/bridge_commands/COMMAND_SCHEMA_V1.json` — command schema.
- `control/project_tasks/<TASK_ID>.json` — capability-scoped project execution specification.
- `control/bridge_commands/command_bus_poller.py` — canonical read-only GitHub poller source.
- `control/bridge_commands/install_command_bus.py` — command-bus installer.
- `control/tampermonkey_multichat/bridge_server_session_bootstrap.py` — automatic session-route bootstrap wrapper.
- `control/tampermonkey_multichat/bridge_server_status_compaction.py` — nested-status-safe result compaction implementation.

Remote repository writes are made by ChatGPT through the GitHub connector. The WSL side does not autonomously push to GitHub.

### `bas1231/fg-assistent`

The existing DEV tunnel is reused as a transport adapter for project-executor tasks.

For a project task, a matching manifest exists at:

`dev_tasks/<TASK_ID>.json`

The manifest synchronizes the canonical executor and guard and invokes:

`python3 project_task_executor.py <TASK_ID>`

The compatibility command-bus action currently used to enter this DEV path is `SIX_AI_HEALTH`. That action name is a transport compatibility detail; the matching immutable project task defines what the executor may actually do.

## Session routing

Multiple Prediction chats can be active at once, so a global pinned route is not a safe normal addressing mechanism.

A new chat obtains its own route automatically from the existing wake `/next` poll. The browser poll supplies a stable `chat_id` and `consumer_id`. If that chat has no proven route yet, the wake bridge creates a deterministic chat-scoped route and returns an idempotent control message:

`NIGHTSHIFT_WSL_RESULT_V1 task=SESSION-ROUTE-... status=PASS exit=0 kind=SESSION_ROUTE_BOOTSTRAP`

After that exact result appears in the chat, its `SESSION-ROUTE-*` task ID becomes the `route_task_id` for subsequent command-bus tasks from that chat.

Normal commands should therefore carry an explicit session route. `route_task_id:null` is not the normal multi-session mode.

The bootstrap is routing metadata only. It does not execute project code and is deliberately idempotent. Normal command execution remains at-most-once.

## Creating a normal command

ChatGPT creates exactly one new immutable file:

`control/bridge_commands/inbox/<TASK_ID>.json`

The task follows `PREDICTION_BRIDGE_COMMAND_V1` and contains, among other fields:

- unique `task_id`;
- an allowed `action`;
- `created_at_utc`;
- the current chat's explicit `route_task_id`;
- `live_trading:false`;
- `paid_actions:false`;
- `wallet_actions:false`;
- intelligence/provenance metadata.

Task IDs are never edited or reused after dispatch. Different bytes under an already claimed task ID are a conflict.

## WSL command-bus poller

Installed command-bus runtime:

- poller: `~/.local/share/prediction-command-bus/command_bus_poller.py`
- read-only GitHub mirror: `~/.local/share/prediction-command-bus/repo`
- task state: `~/.local/state/prediction-command-bus/tasks/`
- incidents: `~/.local/state/prediction-command-bus/incidents/`
- optional pinned control route: `~/.config/prediction-command-bus/route.json`
- service: `prediction-command-bus.service`
- timer: `prediction-command-bus.timer`

The timer polls GitHub read-only, normally on roughly a 30-second cadence. It does not use the user's production working tree as its fetch target.

Before localhost dispatch the poller writes a durable local claim containing the task identity and remote-content provenance. This creates fail-closed at-most-once dispatch semantics.

Possible transport states include:

- `DISPATCHED` — localhost accepted the command;
- `REJECTED` — deterministic validation or local receiver rejection;
- `AMBIGUOUS` — the request may or may not have arrived after a transport exception; never silently retry;
- `BLOCKED_ROUTE` — no valid route was available, so no dispatch occurred.

`DISPATCHED` is not end-to-end success. Success is only established when the same task ID returns to the intended chat with the required task assertions and `status=PASS exit=0`.

## Project-executor task model

Code changes, tests, local Git work, bounded runtime installs and Prediction user-service work use a second immutable specification:

`control/project_tasks/<TASK_ID>.json`

The same task ID is also used in the matching `bas1231/fg-assistent/dev_tasks/<TASK_ID>.json` transport manifest and command-bus inbox file.

A project task pins a concrete `source_commit`, declares exact capabilities and contains an ordered operation list.

Typical capabilities are:

- `read_repository`
- `write_worktree`
- `run_project_python`
- `run_tests`
- `local_git`
- `read_runtime`
- `write_runtime`
- `user_service_manage`
- `read_logs`

Typical operation types are:

- `write_text`
- `delete`
- `python`
- `git`
- `install_runtime`
- `service`
- `daemon_reload`
- `journal`

Repository mutation happens in an isolated task worktree created from the pinned source commit. Repository-owned Python runs under the project guard. Local Git operations are allowlisted. WSL does not autonomously publish the resulting branch or commit to GitHub.

## Hard execution boundaries

The architecture deliberately does not provide an unrestricted shell.

Always blocked by the normal executor path:

- `sudo`, root or privilege elevation;
- autonomous WSL `git push` or remote-ref mutation;
- credential reads/writes or known credential locations;
- unrestricted external networking from project code;
- live trade/order/cancel/withdraw operations;
- wallet, crypto or fund movement;
- paid API/cloud/subscription actions without the separately required specific approval;
- writes outside the task worktree, task temp space or explicitly allowlisted Prediction runtime paths;
- arbitrary non-Prediction user-service management.

Project tasks also carry explicit fail-closed safety fields such as:

- `live_trading:false`
- `paid_actions:false`
- `wallet_actions:false`
- `remote_git_write:false`
- `credential_write:false`

The command bus cannot widen those rights; the executor specification and guard remain authoritative.

## Result path

After execution, the local DEV/executor result is handed to the wake bridge on `127.0.0.1:8765`.

Normal result delivery uses fail-closed queue semantics:

`outbox -> inflight -> sent`

- `outbox` means not yet leased to the browser;
- `inflight` means leased once; browser delivery can still be confirmed or ambiguous;
- `sent` means browser ACK confirmed;
- `quarantine` preserves legacy/ambiguous evidence and is not treated as successfully delivered.

A normal command result is not silently moved from `inflight` back to `outbox`. Automatic replay could duplicate user-visible delivery or hide ambiguity. Replay is therefore deliberate. The special `SESSION-ROUTE-*` bootstrap announcement has its own bounded idempotent re-announcement rule because it executes no project command.

The result compactor treats the outer DEV task status as authoritative so that embedded historical logs containing old `FAIL`, `TaskError` or non-zero RC markers cannot incorrectly flip a successful current diagnostic to failure.

## Proven end-to-end code execution — 2026-09-29

This architecture has now been proven with an actual code execution round trip from a fresh chat-scoped route.

Automatic route bootstrap observed in the issuing chat:

`NIGHTSHIFT_WSL_RESULT_V1 task=SESSION-ROUTE-9f9fd46c002c07a145f8dd11 status=PASS exit=0 kind=SESSION_ROUTE_BOOTSTRAP`

That route was then used explicitly by:

`DEV-PRED-BUS-CODE-ROUNDTRIP-20260929-E001`

GitHub evidence:

- command file: `control/bridge_commands/inbox/DEV-PRED-BUS-CODE-ROUNDTRIP-20260929-E001.json`
- project task: `control/project_tasks/DEV-PRED-BUS-CODE-ROUNDTRIP-20260929-E001.json`
- DEV transport manifest: `bas1231/fg-assistent/dev_tasks/DEV-PRED-BUS-CODE-ROUNDTRIP-20260929-E001.json`
- pinned source commit: `0f90a20e7cbb02eb2308a9b917d571f110b0fadb`

The project task required only:

- `read_repository`
- `write_worktree`
- `run_project_python`

It wrote repository-owned Python at:

`control/dev_checks/bus_code_roundtrip_e001.py`

That program wrote the token:

`PREDICTION_BUS_WSL_CODE_OK_20260929_E001`

into an isolated-worktree runtime file, read it back, asserted exact equality and printed a deterministic SHA-256. If the write/readback assertion or Python invocation failed, the task could not return a clean RC 0.

Observed result in the same originating chat:

`NIGHTSHIFT_WSL_RESULT_V1 task=DEV-PRED-BUS-CODE-ROUNDTRIP-20260929-E001 status=PASS exit=0 rcs=1:0 head=0f90a20e7cbb02eb2308a9b917d571f110b0fadb event=1790703629-2f38056151b5`

This proves the complete operational path:

`ChatGPT -> private GitHub command bus -> read-only WSL poller/router -> DEV transport -> capability-scoped project executor -> repository-owned Python execution in WSL -> result bridge -> same ChatGPT session`

It also proves that the task executed against the intended pinned source commit and that the executed command returned RC 0.

This is operational evidence. It does **not** by itself complete the separate formal independent Tier-A qualification record and does not relax any trading, cost, wallet, credential, network or privilege boundary.

## What future ChatGPT sessions should do

For normal Prediction work that may require WSL:

1. Read `00_CHATGPT_START_HERE.md` and the current canonical documents listed there.
2. Obtain or observe the automatic `SESSION-ROUTE-*` PASS for the current chat.
3. Reuse that route explicitly on every subsequent command from the session.
4. For code/build/test work, create the same fresh task ID across project task, DEV manifest and command-bus inbox.
5. Declare only the capabilities and operations required by the task.
6. Keep all normal safety flags false.
7. Treat dispatch as transport progress only.
8. Claim success only after the same task ID returns to the intended chat with `status=PASS exit=0` and task-specific assertions/tests have actually run.
9. On failure, diagnose through a fresh immutable task before falling back to manual terminal intervention.

## Related canonical documents

- `control/bridge_commands/CURRENT_STATE.md` — latest observed runtime/evidence state.
- `control/bridge_commands/SESSION_ROUTING.md` — session-specific addressing rules.
- `control/bridge_commands/OPERATIONS.md` — command-bus transport semantics and local runtime paths.
- `control/bridge_commands/COMMAND_SCHEMA_V1.json` — command schema.
- `control/NEW_SESSION_LOCAL_EXECUTION.md` — step-by-step task creation and dispatch procedure.
- `control/PROJECT_EXECUTOR.md` — executor capabilities, operations and hard boundaries.
- `control/tampermonkey_multichat/PROTOCOL.md` — complete chat/WSL bridge protocol.
