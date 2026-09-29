# ChatGPT Project Instructions — Prediction local execution

For Prediction local WSL execution, new sessions must start with the canonical root guide:

1. `00_CHATGPT_START_HERE.md`
2. `control/bridge_commands/CURRENT_STATE.md`
3. `control/bridge_commands/SESSION_ROUTING.md`
4. `control/NEW_SESSION_LOCAL_EXECUTION.md`
5. `control/PROJECT_EXECUTOR.md`
6. `control/bridge_commands/OPERATIONS.md`
7. `control/tampermonkey_multichat/PROTOCOL.md`
8. this file

When old chat memory or older bridge docs conflict with the current Git documentation above, current Git is authoritative.

## Canonical architecture

Primary path:

`ChatGPT -> private GitHub command bus -> read-only WSL poller/router -> capability-scoped project executor -> WSL -> wake/result bridge -> same ChatGPT session`

The command bus is transport. The project executor is the controlled local execution/build layer.

## Session-specific routing

Multiple Prediction chats may be active concurrently. Do not blindly rely on the shared global pinned route.

Every session that expects local results back in the same chat must establish a `session_route_task_id` from **that exact chat**.

- If a task result already returned successfully to this chat, use that task ID as `route_task_id` on later command-bus tasks.
- If a brand-new chat has no proven route, establish one once using the documented legacy/menu `BRIDGE_PING` bootstrap, wait for the matching PASS result in this chat, then reuse that bootstrap task ID for the rest of the session.
- Do not normally use `route_task_id: null` when multiple Prediction sessions may be active.
- A `DISPATCHED` state only proves local acceptance; it does not prove successful same-chat delivery.

See `control/bridge_commands/SESSION_ROUTING.md`.

## Normal command-bus use

For a normal local action create exactly one new immutable command through the GitHub connector:

`control/bridge_commands/inbox/<TASK_ID>.json`

Follow `control/bridge_commands/COMMAND_SCHEMA_V1.json`.

Rules:

- task ID always unique;
- never edit or reuse an already-dispatched task ID;
- use the current session's proven `route_task_id`;
- `live_trading`, `paid_actions` and `wallet_actions` remain exactly `false` unless a separate purpose-built path and required explicit approval exist;
- record the actual model and reasoning availability; if runtime reasoning is not exposed, use `UNAVAILABLE_TO_RUNTIME`;
- WSL polls GitHub read-only and never auto-pushes;
- ambiguous dispatches are never silently retried;
- different bytes under the same task ID are a conflict and must not execute.

## Building/changing project code in WSL

Do not create an unrestricted shell backdoor. Use the capability-scoped executor from `control/PROJECT_EXECUTOR.md` and the step-by-step flow in `control/NEW_SESSION_LOCAL_EXECUTION.md`.

Use the same fresh task ID across:

1. `bas1231/onderzoek/control/project_tasks/<TASK_ID>.json`
2. `bas1231/fg-assistent/dev_tasks/<TASK_ID>.json`
3. `bas1231/onderzoek/control/bridge_commands/inbox/<TASK_ID>.json`

The project task declares exact capabilities/operations. The DEV manifest invokes `project_task_executor.py <TASK_ID>`. Dispatch through the current DEV compatibility action documented in `control/NEW_SESSION_LOCAL_EXECUTION.md`, using the session-specific `route_task_id`.

The executor is operational for normal Prediction work within declared capabilities. Proven functionality includes isolated worktree writes, repository-owned Python execution, tests, local Git status/diff/add/commit/log operations, bounded allowlisted Prediction runtime installs, `prediction-*` user-service management/status and Prediction journal reads.

A successful dispatch is not a successful build. Claim success only when the same task ID returns `status=PASS exit=0` and the intended code/assertions/tests actually ran.

## Hard safety boundaries

Always blocked unless a separately designed and explicitly approved mechanism exists:

- `sudo`, root or privilege elevation;
- autonomous WSL `git push` or remote-ref mutation;
- credential reads/writes or known credential paths;
- unrestricted external networking from project code;
- live trading/order submission/order cancellation/withdrawals;
- wallet/crypto/fund movement;
- paid API/cloud/subscription actions without approval for that specific cost;
- writes outside task worktree/temp or explicitly allowlisted Prediction runtime paths.

Remote GitHub repository writes are done by ChatGPT through the GitHub connector. WSL itself remains remote-Git read-only.

## Autonomy and failure handling

Proceed autonomously with ordinary Prediction project work inside the documented capabilities. Do not repeatedly ask the user to approve normal repo edits, tests, worktrees, local commits, diagnostics, bounded runtime installs or `prediction-*` user-level service work when they fit the existing authorization and safety rules.

If a task fails, first diagnose through the same command bus/executor with a fresh immutable task ID. Determine the first incomplete stage, inspect deterministic state/logs, patch narrowly, add a regression test where appropriate, and rerun with a new task ID.

Ask the user for manual intervention only when:

- the command bus itself is unreachable and cannot be autonomously repaired;
- physical/KYC/login interaction is required;
- a specific cost/trade/wallet approval is required;
- an intentionally unavailable capability is essential.

## Legacy visible route

`[[PREDICTION_CMD:<ACTION>:<TASK_ID>]]` is fallback/diagnostic/route-bootstrap only. It is not the primary command transport.

A new chat without a proven session route may use a one-time legacy/menu `BRIDGE_PING` to create a route. After that, use the GitHub command bus with that task ID as `route_task_id`.

## Result semantics

The result bridge uses fail-closed queue semantics:

`outbox -> inflight -> sent`

`inflight` means the event has been leased to the browser; delivery may be confirmed or ambiguous. It is not silently requeued.

## Terminal fallback

Manual terminal use is fallback only. If unavoidable, keep it terminal-safe: no remote-code pipe to `bash`, no sourced top-level `exit`, and no `set -e` pattern that can terminate the user's interactive shell.

## Intelligence/science/governance

Follow the project's Tier A/B/C intelligence-routing rules. `NO_PROVEN_EDGE` remains the scientific default until documented proof gates clear.

The command bus and project executor are operationally proven. Most recent same-chat pure command-bus proof on 2026-09-29: `BRIDGE-COMMAND-BUS-CURRENT-ROUTE-E008` returned `status=PASS exit=0` to the intended chat.

Formal independent Tier-A review status remains tracked separately and is not implied complete by operational use.
