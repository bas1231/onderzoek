# Prediction — ChatGPT START HERE

**Mandatory first read for every new Prediction ChatGPT session that may need local WSL execution.**

Do not rediscover the local bridge, ask the user to paste normal build commands into WSL, or fall back to the old visible DOM command path as the primary method.

## Canonical execution architecture

The installed operational path is:

`ChatGPT -> private GitHub command bus -> read-only WSL poller/router -> capability-scoped project executor -> WSL -> wake/result bridge -> same ChatGPT session`

The **command bus is transport**. The **project executor is the controlled local build/execution layer**.

## Mandatory read order

Before doing local Prediction work, read these files from `bas1231/onderzoek`:

1. `00_CHATGPT_START_HERE.md` — this file.
2. `control/bridge_commands/CURRENT_STATE.md` — current proven state and evidence.
3. `control/bridge_commands/SESSION_ROUTING.md` — mandatory same-chat routing rule.
4. `control/NEW_SESSION_LOCAL_EXECUTION.md` — step-by-step execution flow.
5. `control/PROJECT_EXECUTOR.md` — executor capabilities and hard boundaries.
6. `control/bridge_commands/OPERATIONS.md` — command-bus operations.
7. `control/tampermonkey_multichat/PROTOCOL.md` — canonical bridge protocol.
8. `control/tampermonkey_multichat/CHATGPT_PROJECT_INSTRUCTIONS.md` — full project-specific bridge instructions.

When old chat memory or older docs conflict with these files, the current Git documentation above is authoritative.

## Session routing: do this first

Multiple Prediction chats may exist at the same time. Never assume the global pinned route points to the current chat.

For every chat session that expects WSL results back in that same chat:

1. Establish a `session_route_task_id` from **this exact chat**.
2. If this chat already has a task whose result demonstrably returned here, reuse that task ID as `route_task_id` for subsequent command-bus tasks.
3. If this is a brand-new chat with no proven route, create one once using the documented legacy/menu `BRIDGE_PING` bootstrap path, wait for the matching `NIGHTSHIFT_WSL_RESULT_V1 ... status=PASS exit=0`, then use that bootstrap task ID as the session route for the rest of the chat.
4. Do not normally use `route_task_id: null` when more than one Prediction chat may be active.

A task is successful only when the same task ID returns to the intended chat with the expected status and assertions. `DISPATCHED` alone is not success.

## Normal command-bus use

For a local command, create exactly one fresh immutable file through the ChatGPT GitHub connector:

`control/bridge_commands/inbox/<TASK_ID>.json`

Use `control/bridge_commands/COMMAND_SCHEMA_V1.json`.

Rules:

- task IDs are unique and never reused or edited after dispatch;
- use the current session's proven `route_task_id`;
- keep `live_trading:false`, `paid_actions:false`, and `wallet_actions:false` unless a separate purpose-built path and explicit user approval exist;
- WSL fetches GitHub read-only and never auto-pushes;
- ambiguous dispatches are not silently retried;
- record actual model/reasoning provenance; when reasoning level is not exposed, use `UNAVAILABLE_TO_RUNTIME`.

## Building or changing code in WSL

For project code, tests, local Git work, runtime installs or Prediction user-service management, use the **capability-scoped project executor**, not an unrestricted shell.

Create the same fresh task ID in all three layers:

1. `bas1231/onderzoek/control/project_tasks/<TASK_ID>.json`
2. `bas1231/fg-assistent/dev_tasks/<TASK_ID>.json`
3. `bas1231/onderzoek/control/bridge_commands/inbox/<TASK_ID>.json`

The project task declares the required capabilities and operations. The DEV manifest invokes `project_task_executor.py <TASK_ID>`. The command-bus dispatch currently uses the compatibility action documented in `control/NEW_SESSION_LOCAL_EXECUTION.md` and carries the session-specific `route_task_id`.

Operationally proven executor capabilities include:

- isolated worktree file writes/changes;
- repository-owned Python execution;
- tests;
- local Git status/diff/add/commit/log operations;
- bounded allowlisted Prediction runtime installs;
- `prediction-*` user-service inspection/management;
- Prediction journal/log reads.

Do not claim a build succeeded merely because it was dispatched. Require the same task ID to return `status=PASS exit=0` and require task-specific assertions/tests to have run.

## Hard boundaries

Do not bypass these with a broader shell or alternate route:

- no `sudo`/root/privilege elevation;
- no autonomous WSL `git push` or remote-ref mutation;
- no credential reads/writes or known credential paths;
- no unrestricted external networking from project code;
- no live trades/orders/cancellations/withdrawals;
- no wallet/crypto/fund movement;
- no paid API/cloud/subscription action without explicit approval for that specific cost;
- no writes outside task worktree/temp or explicitly allowlisted Prediction runtime paths.

Remote GitHub repository writes are performed by ChatGPT through the GitHub connector, not by autonomous WSL processes.

## Failure handling

Do not immediately ask the user for terminal commands.

First diagnose through the same command-bus/executor system with a fresh immutable task ID. Determine the first incomplete stage, inspect deterministic state/logs, patch narrowly, add a regression test when a safety/execution bug is found, and rerun with a new task ID.

Ask the user for manual intervention only when:

- the command bus itself is unreachable and cannot be autonomously repaired;
- physical/KYC/login interaction is required;
- a specific cost/trade/wallet approval is required;
- an intentionally unavailable capability is essential.

## Terminal fallback

Manual WSL commands are fallback only. If unavoidable, keep them terminal-safe: no remote-code pipe to `bash`, no sourced top-level `exit`, and no `set -e` pattern that can terminate the user's interactive shell.

## Scientific and governance defaults

- `NO_PROVEN_EDGE` remains the scientific default until evidence clears the project's gates.
- Follow Tier A/B/C intelligence routing and provenance requirements.
- Operational use of the bridge/executor does not imply that the formal independent Tier-A review record is complete.

## Current proven baseline

The command bus and project executor have passed end-to-end operational tests. The most recent same-chat pure command-bus proof on 2026-09-29 was `BRIDGE-COMMAND-BUS-CURRENT-ROUTE-E008`, which returned `status=PASS exit=0` to the intended chat. See `control/bridge_commands/CURRENT_STATE.md` for the full current evidence.
