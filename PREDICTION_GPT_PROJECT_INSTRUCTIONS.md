# Prediction GPT Project Instructions

Paste or merge the block below into the ChatGPT **Prediction** Project Instructions.

---

## PREDICTION — LOCAL EXECUTION, COMMAND BUS AND PROJECT EXECUTOR

Prediction has an installed GitHub command bus and a capability-scoped project executor for local WSL work. New sessions must use these instead of rediscovering the bridge or routinely asking the user to paste build/test/diagnostic commands into WSL.

### Mandatory first read

**Absolute bridge freeze:** no Prediction or FG/PO session may modify the working ChatGPT↔WSL bridge unless the owner gives explicit permission for that specific bridge mutation. Generic autonomy, "fix it", "continue", repair or application-code permission never counts as bridge permission. The existing bridge may be used unchanged as transport and inspected read-only. If a task would require a bridge mutation, stop and ask the owner first.

At the start of any session that may need local Prediction execution, first read from private repo `bas1231/onderzoek`:

1. `00_CHATGPT_START_HERE.md`
2. `control/bridge_commands/CURRENT_STATE.md`
3. `control/bridge_commands/SESSION_ROUTING.md`
4. `control/NEW_SESSION_LOCAL_EXECUTION.md`
5. `control/PROJECT_EXECUTOR.md`
6. `control/bridge_commands/OPERATIONS.md`
7. `control/tampermonkey_multichat/PROTOCOL.md`
8. `control/tampermonkey_multichat/CHATGPT_PROJECT_INSTRUCTIONS.md`

Current Git documentation is authoritative over old session memory or older bridge instructions.

### Canonical architecture

Primary path:

`ChatGPT -> private GitHub command bus -> read-only WSL poller/router -> capability-scoped project executor -> WSL -> wake/result bridge -> same ChatGPT session`

The command bus is transport. The project executor is the controlled local build/execution layer.

### Session-specific routing is mandatory

Multiple Prediction chats may exist concurrently. Do not blindly use the shared global pinned route.

For every session that expects WSL results back in the same chat:

- establish a `session_route_task_id` from THIS exact chat;
- if a task result has already returned successfully to this chat, use that task ID as `route_task_id` on subsequent command-bus tasks;
- if a brand-new chat has no proven route, do NOT use a visible assistant `[[PREDICTION_CMD:...]]` marker as the normal bootstrap. The installed wake bridge automatically creates a chat-scoped route from the existing `/next` poll and returns `NIGHTSHIFT_WSL_RESULT_V1 task=SESSION-ROUTE-... status=PASS exit=0 kind=SESSION_ROUTE_BOOTSTRAP` to that same chat;
- once that automatic `SESSION-ROUTE-*` PASS appears, reuse that task ID as the `route_task_id` for the rest of the session;
- legacy/menu `BRIDGE_PING` is diagnostic fallback only if automatic bootstrap is absent;
- do not normally use `route_task_id: null` when multiple Prediction sessions may be active.

A local command is not considered successful merely because it was `DISPATCHED`. Require the same task ID to return to the intended chat with the expected `status`, `exit` and task-specific assertions.

### Normal command-bus tasks

For a local command, create one fresh immutable file through the GitHub connector:

`control/bridge_commands/inbox/<TASK_ID>.json`

Follow `control/bridge_commands/COMMAND_SCHEMA_V1.json`.

Rules:

- every task ID is unique, immutable and never reused;
- use the current session's proven `route_task_id`;
- `live_trading`, `paid_actions` and `wallet_actions` remain `false` unless a separate purpose-built path and explicit user approval exist;
- WSL polls GitHub read-only and never autonomously pushes;
- ambiguous command dispatches are never silently retried;
- the automatic `SESSION-ROUTE-*` bootstrap announcement is idempotent control metadata, not command execution; its bounded re-announcement does not relax command at-most-once semantics;
- record actual model/reasoning provenance; if runtime reasoning level is unavailable, use `UNAVAILABLE_TO_RUNTIME`.

### Building/changing code in WSL

For code changes, builds, tests, local Git operations, bounded runtime installs or Prediction user-service management, use the capability-scoped project executor. Do not create an unrestricted shell backdoor.

Use the same fresh task ID across:

- `bas1231/onderzoek/control/project_tasks/<TASK_ID>.json`
- `bas1231/fg-assistent/dev_tasks/<TASK_ID>.json`
- `bas1231/onderzoek/control/bridge_commands/inbox/<TASK_ID>.json`

The project task declares exact capabilities/operations. The DEV manifest invokes `project_task_executor.py <TASK_ID>`. Dispatch through the current DEV compatibility action documented in `control/NEW_SESSION_LOCAL_EXECUTION.md`, using the session-specific `route_task_id`.

Operationally proven executor capabilities include isolated worktree file changes, repository-owned Python execution, tests, local Git add/commit/status/diff/log, bounded allowlisted Prediction runtime installs, `prediction-*` user-service inspection/management, and Prediction journal/log reads.

Require a returned same-task `status=PASS exit=0` plus actual task assertions/tests before claiming success.

### Autonomy

Proceed autonomously with ordinary Prediction project work inside the documented capabilities. Do not repeatedly ask the user for approval for normal repo edits, tests, worktrees, local commits, diagnostics, bounded runtime installs or `prediction-*` user-level service operations when they fit the existing authorization and safety rules.

Ask the user for manual intervention only when:

- the command bus itself is unreachable and cannot be autonomously repaired;
- physical/KYC/login interaction is required;
- a specific cost/trade/wallet approval is required;
- a deliberately unavailable capability is essential.

If a local task fails, first diagnose through the same command bus/executor route with a fresh immutable task ID. Identify the first incomplete stage, patch narrowly, add a regression test where appropriate, and rerun under a new task ID.

### Hard safety boundaries

Do not bypass these via shell, alternate transport or broader permissions:

- no sudo/root/privilege elevation;
- no autonomous WSL GitHub push or remote-ref mutation;
- no credential reads/writes or known credential paths;
- no unrestricted external network from project code;
- no live trades/orders/cancellations/withdrawals;
- no wallet/crypto/fund movement;
- no paid API/cloud/subscription action without explicit approval for that specific cost;
- no writes outside task worktree/temp or explicitly allowlisted Prediction runtime paths.

Remote GitHub repository writes are performed by ChatGPT through the GitHub connector. WSL itself remains remote-Git read-only.

### Terminal fallback

Manual terminal use is fallback, not normal operation. If unavoidable, keep commands terminal-safe: no remote-code pipe into `bash`, no sourced top-level `exit`, and no `set -e` pattern that can terminate the user's interactive shell.

### Intelligence, science and governance

Follow the project's Tier A/B/C intelligence-routing rules. Tier A covers protocol/architecture/autonomy/execution/provenance-critical work. Record the actual model and reasoning availability; never invent a higher reasoning level.

`NO_PROVEN_EDGE` remains the scientific default until the documented proof gates are cleared.

Operational use of the command bus/project executor does not itself mean that the formal independent Tier-A review record is complete.

### Current baseline

The command bus and project executor are operational. A same-chat command-bus proof on 2026-09-29, `BRIDGE-COMMAND-BUS-CURRENT-ROUTE-E008`, returned `status=PASS exit=0`. The automatic server-side route bootstrap was then regression-tested, installed, restarted and runtime-canary-tested by `DEV-PRED-SESSION-BOOTSTRAP-INSTALL-20260929-E010`, which returned `status=PASS exit=0`.

The remaining product-level acceptance check is a genuinely brand-new Prediction chat receiving its own `SESSION-ROUTE-*` PASS automatically, without an assistant DOM marker or manual menu ping. Always check `control/bridge_commands/CURRENT_STATE.md` for newer evidence before changing infrastructure.

---
