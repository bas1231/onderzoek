# Prediction — New Session Local Execution Guide

Status: canonical operating guide for new ChatGPT sessions.
Updated: 2026-09-29 after automatic route-bootstrap install PASS.

## Purpose

A new Prediction session must not rediscover how ChatGPT reaches WSL. The installed path is already operational and should be used directly for normal build, test, diagnose and user-level management work.

Primary control path:

`ChatGPT -> private GitHub bas1231/onderzoek -> read-only WSL command-bus poller -> localhost router/receiver -> project executor / approved local action -> wake/result bridge -> same ChatGPT session`

GitHub remote writes are done by ChatGPT through the GitHub connector. Autonomous WSL processes remain GitHub read-only and do not push.

## Mandatory read order for a new session

Read:

1. `00_CHATGPT_START_HERE.md`
2. `control/bridge_commands/CURRENT_STATE.md`
3. `control/bridge_commands/SESSION_ROUTING.md`
4. `control/bridge_commands/OPERATIONS.md`
5. `control/PROJECT_EXECUTOR.md`
6. `control/tampermonkey_multichat/PROTOCOL.md`
7. `control/tampermonkey_multichat/CHATGPT_PROJECT_INSTRUCTIONS.md`
8. `control/build_log/PROTOCOL.md`

Treat current Git documentation as canonical over old chat memory or obsolete bridge instructions.

## Shared build log before dispatch

Before creating a new build, repair, or diagnostic task, inspect open events in `control/build_log/events/`.

Continue the same `work_item_id` when the objective is the same. Add a `PLAN` or `ATTEMPT` event before dispatch and a `RESULT` event after the result returns. On failure or handoff, record the first incomplete step and the next action. Do not repeat an earlier successful step merely because another ChatGPT session takes over.

The dashboard Logboek page is the human-facing view of this ledger.

## Step 0 — establish the current chat route

Before dispatching a task that must return to this chat, establish a `session_route_task_id` for this exact chat.

- If a previous task result demonstrably returned successfully to this chat, use that task ID.
- If this is a brand-new chat with no proven route, the installed wake bridge now automatically bootstraps one from the browser's existing `/next` poll. Wait for:

  `NIGHTSHIFT_WSL_RESULT_V1 task=SESSION-ROUTE-... status=PASS exit=0 kind=SESSION_ROUTE_BOOTSTRAP`

- Use that `SESSION-ROUTE-*` task ID as `route_task_id` on subsequent command-bus tasks from this chat.
- Do not emit a visible assistant `[[PREDICTION_CMD:...]]` marker as the normal bootstrap procedure.
- Legacy/menu `BRIDGE_PING` is diagnostic fallback only if the automatic bootstrap does not appear.
- Do not normally use `route_task_id: null` when multiple Prediction sessions may exist.

The shared pinned route is not a reliable same-chat addressing mechanism in a multi-session setup. See `control/bridge_commands/SESSION_ROUTING.md`.

The automatic bootstrap is idempotent control metadata, not command execution. Normal commands retain their durable at-most-once semantics.

## When to use the plain command bus

Use `control/bridge_commands/inbox/<TASK_ID>.json` for approved local actions such as a bridge ping or the current DEV transport adapter.

Rules:

- every task ID is unique and immutable;
- never edit or reuse a dispatched command task ID;
- use the current session's proven `route_task_id`;
- `live_trading`, `paid_actions`, and `wallet_actions` are explicit `false` unless a separate user approval and purpose-built path exists;
- record intelligence tier, actual model and actual reasoning availability; use `UNAVAILABLE_TO_RUNTIME` rather than inventing a value;
- an ambiguous command dispatch is not automatically retried.

## How to execute project code in WSL

Do not create an unrestricted shell backdoor. Use the capability-scoped project executor.

### Step 1 — preregister the project task in `bas1231/onderzoek`

Create exactly one immutable file:

`control/project_tasks/<TASK_ID>.json`

Schema: `PREDICTION_PROJECT_TASK_V1`.

Pin a real `source_commit`. Declare only the required capabilities and operations. Safety fields stay fail-closed:

```json
"safety": {
  "live_trading": false,
  "paid_actions": false,
  "wallet_actions": false,
  "remote_git_write": false,
  "credential_write": false
}
```

Common capabilities:

- `read_repository`
- `write_worktree`
- `run_project_python`
- `run_tests`
- `local_git`
- `read_runtime`
- `write_runtime`
- `user_service_manage`
- `read_logs`

Common operations:

- `write_text`
- `delete`
- `python`
- `git`
- `install_runtime`
- `service`
- `daemon_reload`
- `journal`

Repository code runs in an isolated worktree under the project-executor runtime, not directly in `~/prediction_research_prod`.

### Step 2 — create the matching DEV transport manifest

Create a matching immutable file in private repo `bas1231/fg-assistent`:

`dev_tasks/<TASK_ID>.json`

It must sync the canonical executor/guard and invoke:

`python3 project_task_executor.py <TASK_ID>`

Minimal pattern:

```json
{
  "schema": "DEV_TASK_V1",
  "task_id": "<TASK_ID>",
  "project": "fg_assistent",
  "live_trading": false,
  "paid_actions": false,
  "network_devices": false,
  "sync": {
    "ref": "origin/main",
    "paths": [
      "project_task_executor.py",
      "project_task_guard/sitecustomize.py"
    ]
  },
  "commands": [
    {
      "argv": ["python3", "project_task_executor.py", "<TASK_ID>"],
      "timeout_seconds": 300
    }
  ]
}
```

### Step 3 — dispatch through the primary GitHub command bus

Create:

`control/bridge_commands/inbox/<TASK_ID>.json`

The current DEV adapter is dispatched with action `SIX_AI_HEALTH` and the exact same task ID. This name is a transport compatibility detail; the matching DEV manifest determines the executor invocation.

Example:

```json
{
  "schema": "PREDICTION_BRIDGE_COMMAND_V1",
  "task_id": "<TASK_ID>",
  "action": "SIX_AI_HEALTH",
  "created_at_utc": "<UTC timestamp>",
  "route_task_id": "<SESSION_ROUTE_TASK_ID_FROM_THIS_CHAT>",
  "live_trading": false,
  "paid_actions": false,
  "wallet_actions": false,
  "intelligence_tier": "C",
  "issuer": {
    "model": "<actual model>",
    "reasoning_level": "UNAVAILABLE_TO_RUNTIME"
  }
}
```

The WSL poller normally sees new commands within roughly 30 seconds.

## Result semantics

A successful local execution returns through the wake bridge with the same task ID, for example:

`NIGHTSHIFT_WSL_RESULT_V1 task=<TASK_ID> status=PASS exit=0 ...`

Do not treat mere dispatch as success. For code execution require the executor task itself to return `PASS`/exit `0` and make the task's intended observable assertion part of the code or operation sequence.

For a fresh code-execution proof, prefer a harmless task that writes a repository-owned Python file in an isolated worktree, executes it, writes/reads back an artifact, asserts exact content and returns exit 0 only when the assertions pass.

## What the executor is allowed to manage

Within explicitly declared capabilities it can:

- write/change project files in isolated worktrees;
- execute repository-owned Python;
- run tests;
- make local Git add/commit/status/diff/log operations;
- atomically install allowlisted Prediction runtime files;
- manage or inspect `prediction-*` user-level systemd units;
- read Prediction user journals/logs.

The executor has a repository-local Git identity for its isolated worktrees. It must not mutate the user's global Git identity.

## Hard boundaries

Do not bypass these via a broader shell:

- no `sudo`, root or privilege elevation;
- no autonomous WSL `git push` or remote-ref mutation;
- no credential reads/writes or known credential paths;
- no unrestricted external network from project code;
- no live trading/orders/cancellations/withdrawals;
- no wallet/crypto/fund movement;
- no paid API/cloud/subscription action without specific user approval;
- no writes outside task worktree/temp or allowlisted Prediction runtime paths.

When a requested action falls outside these capabilities, fail closed and ask only for the missing approval/capability actually required.

## Failure handling

Do not immediately ask the user to run terminal commands.

First use the same automation path to diagnose:

1. determine whether the immutable command was claimed/dispatched;
2. determine whether the matching DEV manifest existed;
3. inspect executor state/receipt with a deterministic diagnostic task;
4. classify the first incomplete operation;
5. make one targeted fix;
6. add a regression test when the failure exposed a safety or execution bug;
7. rerun with a fresh task ID and the current session route.

Ask for manual intervention only when the command bus itself is unreachable and cannot be repaired autonomously, physical/KYC/login interaction is required, a specific cost/trade/wallet approval is required, or an intentionally unavailable capability is essential.

## Terminal fallback

Manual terminal use is fallback, not normal operation. If unavoidable, keep it terminal-safe: no remote-code pipe into `bash`, no sourced top-level `exit`, and no `set -e` pattern that can terminate the user's interactive shell.

## Current proven baseline

See `control/bridge_commands/CURRENT_STATE.md` for current evidence. Explicit same-chat routing and command-bus execution are proven by `BRIDGE-COMMAND-BUS-CURRENT-ROUTE-E008` -> PASS. Automatic new-session route bootstrap was regression-tested, installed, restarted, service-checked and runtime-canary-tested by `DEV-PRED-SESSION-BOOTSTRAP-INSTALL-20260929-E010` -> PASS. The remaining product-level acceptance test is a genuinely new chat receiving its automatic `SESSION-ROUTE-*` PASS without DOM marker/manual ping.
