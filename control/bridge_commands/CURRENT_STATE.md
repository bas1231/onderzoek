# Prediction Command Bus — Current State

Updated: 2026-09-29
Task: `TIERA-BRIDGE-COMMAND-BUS-20260929-E001`
Intelligence tier: A
Implementation model: GPT-5.6 Sol
Actual reasoning level: `UNAVAILABLE_TO_RUNTIME`
Qualification: `REQUIRES_HIGH_INTELLIGENCE_REVIEW`

## Current operational status

The local command bus bootstrap completed successfully with `BOOTSTRAP_RC=0`. The terminal-safe installer preserved the hardened wake wrapper, patched the queue semantics in the underlying `bridge_server_v2.py`, installed the read-only GitHub poller and activated the systemd timer.

Automated end-to-end verification passed without manual dispatch:

`NIGHTSHIFT_WSL_RESULT_V1 task=BRIDGE-BUS-AUTO-20260929-E001 status=PASS exit=0 event=1790680366-d92bee7475cb`

A fresh session-specific route verification on 2026-09-29 also passed:

`NIGHTSHIFT_WSL_RESULT_V1 task=TM-PING-1790690332005 status=PASS exit=0 event=1790690348-70b82c023090`

Using that exact known-good route, the primary GitHub command bus was then re-tested end-to-end:

`NIGHTSHIFT_WSL_RESULT_V1 task=BRIDGE-COMMAND-BUS-CURRENT-ROUTE-E008 status=PASS exit=0 event=1790690527-75b1ec98e0b6`

This proves the active primary path:

`ChatGPT assistant -> private GitHub command file -> read-only WSL poller -> localhost router/receiver -> WSL execution -> wake bridge -> same ChatGPT session route`

## Proven baseline

`BRIDGE-BUS-E001` first proved assistant -> private GitHub -> WSL -> local executor -> wake bridge -> ChatGPT with `BRIDGE_PONG`, exit code 0 and PASS.

The main failure found in the legacy result path was head-of-line blocking: an old ambiguous outbox event could be offered repeatedly and prevent newer events from being delivered.

The installed result queue now uses fail-closed `outbox -> inflight -> sent` semantics in the base queue implementation. The hardened v0.8 wrapper remains responsible for compact delivery formatting, task dedupe and heartbeat behaviour.

## Session routing incident and rule

A later test exposed a separate multi-session routing problem: commands could execute correctly while their result was routed to an older/global pinned ChatGPT route rather than the session that issued the command. The local bridge services themselves remained healthy; the issue was addressing, not WSL execution.

Current canonical rule:

- every active Prediction chat/session should establish a task whose result is proven to return to that same chat;
- use that task as explicit `route_task_id` for subsequent command-bus work in that session;
- do not rely on `route_task_id:null` for normal build/test/diagnostic work when multiple Prediction sessions may exist;
- a fresh session may bootstrap its route once through the documented fallback/menu ping, then reuse that successful task ID explicitly;
- never reuse an already-claimed task to repair delivery; create a new immutable task ID.

Canonical routing documentation: `control/bridge_commands/SESSION_ROUTING.md`.

The successful pair `TM-PING-1790690332005` -> `BRIDGE-COMMAND-BUS-CURRENT-ROUTE-E008` is current functional evidence that explicit session routing works end-to-end.

## Project executor operational proof

The capability-scoped Prediction project executor is operational for day-to-day project build/management work. It has passed deterministic safety tests and live WSL canaries.

Successful evidence:

- `DEV-PRED-PROJECT-EXEC-INSTALL-E002`: PASS, exit 0, compile + full unittest suite green;
- `DEV-PRED-PROJECT-EXEC-CANARY-E001`: PASS, exit 0; isolated worktree creation, repository-owned Python write/execute and local Git inspection proven;
- `DEV-PRED-PROJECT-EXEC-OPS-E003`: PASS, exit 0; project Python execution, isolated local Git commit, bounded runtime install, `prediction-*` user-service inspection and Prediction journal-read path proven;
- local Git identity for executor worktrees is repo-local only (`Prediction Project Executor <prediction-executor@local.invalid>`), not a global user Git mutation.

The executor may therefore be used operationally for ordinary Prediction project work within its declared capabilities. Existing hard guardrails remain unchanged: no live trading, no paid actions, no wallet/crypto actions, no credential writes, no unrestricted root/sudo, and no autonomous remote Git push from WSL.

Formal Tier-A qualification is still recorded separately as `REQUIRES_HIGH_INTELLIGENCE_REVIEW`; operational use does not convert that governance record into a completed independent review.

## Canonical implementation

- `OPERATIONS.md` — operator/new-session guide.
- `SESSION_ROUTING.md` — canonical per-session result-routing rule.
- `COMMAND_SCHEMA_V1.json` — immutable command schema.
- `command_bus_poller.py` — read-only GitHub poller with durable local at-most-once claims.
- `patch_wake_inflight.py` — wrapper-aware queue patch; hardened wrapper stays intact and `bridge_server_v2.py` receives the inflight semantics.
- `install_command_bus.py` — backup, evidence-preserving migration, wrapper/base-aware rollback, service install.
- `bootstrap_local_terminal_safe.sh` — canonical terminal-safe bootstrap.
- `selftest.py` — deterministic offline tests for direct-base and hardened-wrapper layouts.
- `HARDENED_V8_INTEGRATION.md` — v0.8 wrapper integration rationale.
- `inbox/BRIDGE-BUS-AUTO-20260929-E001.json` — automated post-install BRIDGE_PING used for the successful E2E proof.

Canonical protocol and ChatGPT project instructions prefer the GitHub command bus over the legacy DOM marker route.

## How new ChatGPT sessions operate it

1. Read `control/bridge_commands/CURRENT_STATE.md`.
2. Read `control/bridge_commands/SESSION_ROUTING.md`.
3. Read `control/bridge_commands/OPERATIONS.md`.
4. Read `control/NEW_SESSION_LOCAL_EXECUTION.md`, `control/PROJECT_EXECUTOR.md`, `control/tampermonkey_multichat/PROTOCOL.md` and `CHATGPT_PROJECT_INSTRUCTIONS.md` as applicable.
5. Establish one session-specific route task whose result is proven to have returned to the current chat.
6. For a normal local command, create one new immutable file under `control/bridge_commands/inbox/<TASK_ID>.json` using `COMMAND_SCHEMA_V1.json` and set `route_task_id` to the proven current-session route.
7. Do not edit or reuse a previous task ID.
8. WSL polls GitHub read-only and normally picks up the command automatically within roughly 30 seconds.
9. Claim success only when the same task ID returns through the wake bridge with the expected result.
10. The old visible `[[PREDICTION_CMD:...]]` DOM route is diagnostic/route-bootstrap fallback only.

## Guardrails

- WSL side is GitHub read-only: no automated push or publication.
- no live trading;
- no paid action;
- no wallet/crypto action;
- task IDs are immutable;
- command claims are durable before localhost dispatch;
- ambiguous dispatches are never automatically retried;
- ambiguous result delivery remains in `inflight` and never automatically requeues;
- the production working tree is not used as the command-bus fetch target;
- session routing does not relax any execution, cost, trade, wallet, provenance or credential guardrail.

## Installation evidence

Observed 2026-09-29:

- terminal-safe bootstrap: PASS;
- deterministic self-tests: PASS;
- hardened wake service health: PASS, version 8 and existing guardrails preserved;
- command-bus timer: installed/active as part of successful bootstrap;
- qualification record: written by installer;
- automated command `BRIDGE-BUS-AUTO-20260929-E001`: PASS, exit 0, returned to ChatGPT;
- session route bootstrap `TM-PING-1790690332005`: PASS, exit 0, returned to the intended ChatGPT session;
- explicit current-route command-bus test `BRIDGE-COMMAND-BUS-CURRENT-ROUTE-E008`: PASS, exit 0, returned to the same session;
- bootstrap return code: `0`;
- interactive terminal remained open;
- project executor deterministic suite: PASS;
- project executor runtime canary: PASS;
- project executor operational management canary: PASS.

## Qualification gate

The command bus and capability-scoped project executor are functionally installed and proven end-to-end for operational project work. They remain formally `REQUIRES_HIGH_INTELLIGENCE_REVIEW` until an independent Tier-A review finds no open critical issue. Do not use this provisional qualification state to relax any trading, cost, wallet, provenance, evidence or autonomy guardrail.
