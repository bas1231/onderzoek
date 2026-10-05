# Prediction — ChatGPT START HERE

**Mandatory first read for every new Prediction ChatGPT session that may need local WSL execution.**

Do not rediscover the local bridge, ask the user to paste normal build commands into WSL, or fall back to the old visible DOM command path as the primary method.

## Canonical execution architecture

The installed operational path is:

`ChatGPT -> private GitHub command bus -> read-only WSL poller/router -> capability-scoped project executor -> WSL -> wake/result bridge -> same ChatGPT session`

The **command bus is transport**. The **project executor is the controlled local build/execution layer**.

A single technical overview of all components, task flow, runtime paths, safety boundaries and end-to-end evidence is maintained at:

`control/bridge_commands/ARCHITECTURE.md`

## Mandatory read order

Before doing local Prediction work, read these files from `bas1231/onderzoek`:

1. `00_CHATGPT_START_HERE.md` — this file.
2. `control/bridge_commands/CURRENT_STATE.md` — current proven state and evidence.
3. `control/bridge_commands/ARCHITECTURE.md` — complete technical view of the local execution chain.
4. `control/bridge_commands/SESSION_ROUTING.md` — mandatory same-chat routing rule.
5. `control/NEW_SESSION_LOCAL_EXECUTION.md` — step-by-step execution flow.
6. `control/PROJECT_EXECUTOR.md` — executor capabilities and hard boundaries.
7. `control/bridge_commands/OPERATIONS.md` — command-bus operations.
8. `control/tampermonkey_multichat/PROTOCOL.md` — canonical bridge protocol.
9. `control/tampermonkey_multichat/CHATGPT_PROJECT_INSTRUCTIONS.md` — full project-specific bridge instructions.
10. `methodology/EDGE_DISCOVERY_MODEL_GATES.md` — mandatory model roles, Astra gates, read-only prospective measurement, and the any-positive-net-edge objective.

When old chat memory or older docs conflict with these files, the current Git documentation above is authoritative.

## Session routing: do this first

Multiple Prediction chats may exist at the same time. Never assume the global pinned route points to the current chat.

For every chat session that expects WSL results back in that same chat:

1. Establish a `session_route_task_id` from **this exact chat**.
2. If this chat already has a task whose result demonstrably returned here, reuse that task ID as `route_task_id` for subsequent command-bus tasks.
3. If this is a brand-new chat with no proven route, **do not use the visible assistant DOM marker as the normal bootstrap**. The installed wake bridge automatically creates a chat-scoped route from the existing `/next` browser poll and returns:

   `NIGHTSHIFT_WSL_RESULT_V1 task=SESSION-ROUTE-... status=PASS exit=0 kind=SESSION_ROUTE_BOOTSTRAP`

4. Wait for that automatic `SESSION-ROUTE-*` PASS to appear in the same chat, then use that task ID as `route_task_id` for the rest of the session.
5. The legacy/menu `BRIDGE_PING` path is diagnostic fallback only if automatic bootstrap does not appear; it is not the default workflow.
6. Do not normally use `route_task_id: null` when more than one Prediction chat may be active.

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
- The economic objective is `ANY_POSITIVE_NET_EDGE_COUNTS`: do not discard a hypothesis merely because the net euro opportunity is small.
- **Canonical mandatory sequence:** `Scout -> selectie -> GPT-5.6 Sol-opzet -> GPT-6 Astra pre-build review -> GPT-5.6 Sol-build -> GPT-6 Astra post-build code-review -> tests en meting -> supervisor -> rapportage`.
- For a selected edge hypothesis, **GPT-5.6 Sol first produces the version-bound experimental design**.
- Exact-version **GPT-6 Astra must approve that design before the real experiment may be built**. `NEEDS_REVISION` returns binding feedback to Sol; Sol revises and resubmits until Astra approves or the candidate is rejected/parked.
- After pre-build approval, **GPT-5.6 Sol is the required experiment builder** and implements the actual edge experiment.
- **Before any substantive experiment test, backtest, validation run, shadow run or measurement may start, exact GPT-6 Astra must review and approve the actually built code/harness.** This is the mandatory `ASTRA_POSTBUILD_REVIEW` gate.
- If Astra rejects or requests revision after the build, Sol processes that feedback, rebuilds a newly bound version and resubmits it to Astra. The loop repeats until Astra approves or the candidate is rejected/parked.
- **Hard invariant:** `NO_TEST_OR_MEASUREMENT_BEFORE_ASTRA_POSTBUILD_APPROVAL`.
- Only after a valid post-build Astra approval may technical/invalidation tests and read-only/shadow measurements begin.
- After tests and measurement, the supervisor/falsifier/reproducer evaluates the immutable evidence and the system reports `EDGE`, `NO_EDGE`, or `NO_PROVEN_EDGE`.
- Any A→Z qualification that tests or measures before the post-build Astra approval is **not a valid full-chain PASS**, even if later steps are green.
- Prospective current-market measurement remains read-only/shadow only and never authorizes orders, cancellations, funds, wallets or paid actions.
- Follow Tier A/B/C intelligence routing and provenance requirements.
- Operational use of the bridge/executor does not imply that the formal independent Tier-A review record is complete.

## Current proven baseline

The command bus and project executor have passed end-to-end operational tests. `BRIDGE-COMMAND-BUS-CURRENT-ROUTE-E008` returned `status=PASS exit=0` to the intended chat. The automatic server-side session bootstrap was installed and runtime-tested by `DEV-PRED-SESSION-BOOTSTRAP-INSTALL-20260929-E010`, which returned `status=PASS exit=0` after regression tests, compile checks, runtime install, service restart/active check and installed-runtime canary.

A later fresh-session proof on 2026-09-29 automatically returned `SESSION-ROUTE-9f9fd46c002c07a145f8dd11 -> PASS` without a manual ping. That exact route was then used for `DEV-PRED-BUS-CODE-ROUNDTRIP-20260929-E001`, which wrote and executed repository-owned Python through the capability-scoped WSL executor and returned to the same chat as `status=PASS exit=0 rcs=1:0` against pinned source commit `0f90a20e7cbb02eb2308a9b917d571f110b0fadb`.

This proves the complete operational code path from a fresh ChatGPT session through GitHub, WSL and back to that same session. See `control/bridge_commands/ARCHITECTURE.md`, `control/bridge_commands/CURRENT_STATE.md` and `control/bridge_commands/SESSION_ROUTING.md` for details and the distinction between operational proof and formal Tier-A qualification.
