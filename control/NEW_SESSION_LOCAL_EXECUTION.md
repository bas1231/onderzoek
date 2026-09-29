# Prediction — New Session Local Execution Guide

Status: canonical operating guide for new ChatGPT sessions.

## Purpose

A new Prediction session must not rediscover how ChatGPT reaches WSL. The installed path is already operational and should be used directly for normal build, test, diagnose and user-level management work.

Primary control path:

`ChatGPT -> private GitHub bas1231/onderzoek -> read-only WSL command-bus poller -> localhost router/receiver -> project executor / approved local action -> wake/result bridge -> same ChatGPT route`

GitHub remote writes are done by ChatGPT through the GitHub connector. Autonomous WSL processes remain GitHub read-only and do not push.

## Mandatory read order for a new session

Before changing local execution infrastructure, read:

1. `control/bridge_commands/CURRENT_STATE.md`
2. `control/bridge_commands/OPERATIONS.md`
3. `control/PROJECT_EXECUTOR.md`
4. `control/tampermonkey_multichat/PROTOCOL.md`
5. `control/tampermonkey_multichat/CHATGPT_PROJECT_INSTRUCTIONS.md`

Treat these files as canonical over old chat memory or obsolete bridge instructions.

## When to use the plain command bus

Use `control/bridge_commands/inbox/<TASK_ID>.json` for approved local actions such as a bridge heartbeat/ping or the current DEV transport adapter.

Rules:

- every task ID is unique and immutable;
- never edit or reuse a dispatched task ID;
- `live_trading`, `paid_actions`, and `wallet_actions` are explicit `false` unless a separate user approval and purpose-built path exists;
- record intelligence tier, actual model and actual reasoning level; use `UNAVAILABLE_TO_RUNTIME` rather than inventing a value;
- an ambiguous dispatch is not automatically retried;
- normally omit `route_task_id` so the pinned route returns to the current configured control chat.

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

Current transport adapter uses the existing asynchronous DEV tunnel. Create a matching immutable file in private repo `bas1231/fg-assistent`:

`dev_tasks/<TASK_ID>.json`

It must sync the canonical executor and guard and invoke:

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
  "route_task_id": null,
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

For a fresh code-execution proof, prefer a harmless task that:

1. writes a small repository-owned Python file into an isolated worktree;
2. executes it with the project executor;
3. writes and reads back an artifact under the worktree;
4. asserts the exact payload;
5. optionally computes a SHA-256;
6. returns exit `0` only if all assertions pass.

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
- no live trading/orders;
- no wallet/crypto/fund movement;
- no paid API/cloud/subscription action without specific user approval;
- no writes outside task worktree/temp or allowlisted Prediction runtime paths.

When a requested action falls outside these capabilities, fail closed and ask only for the missing approval/capability that is actually required.

## Failure handling

Do not immediately ask the user to run terminal commands.

First use the same automation path to diagnose:

1. determine whether the immutable command was claimed/dispatched;
2. determine whether the matching DEV manifest existed;
3. inspect executor state/receipt with a deterministic diagnostic task;
4. classify the first incomplete operation;
5. make one targeted fix;
6. add a regression test when the failure exposed a safety or execution bug;
7. rerun with a fresh task ID.

Ask for manual intervention only when the command bus itself is unreachable and cannot be repaired autonomously, physical/KYC/login interaction is required, or a specific cost/trade/wallet approval is required.

## Terminal fallback

Manual terminal use is fallback, not normal operation. If unavoidable, keep it terminal-safe: no remote-code pipe into `bash`, no sourced top-level `exit`, and no `set -e` pattern that can terminate the user's interactive shell.

## Current proven baseline

See `control/bridge_commands/CURRENT_STATE.md` for current evidence. At the time this guide was written, the command bus, Python execution canary and operational project-management canary had already passed end-to-end. A new session should use the installed system rather than rebuilding it from scratch.
