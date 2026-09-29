# Prediction Command Bus — Current State

Updated: 2026-09-29
Task: `TIERA-BRIDGE-COMMAND-BUS-20260929-E001`
Intelligence tier: A
Implementation model: GPT-5.6 Sol
Actual reasoning level: `UNAVAILABLE_TO_RUNTIME`
Qualification: `REQUIRES_HIGH_INTELLIGENCE_REVIEW`

## Proven before automation

`BRIDGE-BUS-E001` proved assistant -> private GitHub -> WSL -> local executor -> wake bridge -> ChatGPT with `BRIDGE_PONG`, exit code 0 and PASS.

The main failure found in the legacy result path was head-of-line blocking: an old ambiguous outbox event could be offered repeatedly and prevent newer events from being delivered.

## New architecture committed to Git

- `OPERATIONS.md` — operator/new-session guide.
- `COMMAND_SCHEMA_V1.json` — immutable command schema.
- `command_bus_poller.py` — read-only GitHub poller with durable local at-most-once claims.
- `patch_wake_inflight.py` — narrow runtime patch preserving local bridge modifications while adding atomic `outbox -> inflight` claims.
- `install_command_bus.py` — backup, evidence-preserving migration, service install and rollback.
- `bootstrap_local.sh` — one-shot bootstrap from an isolated mirror.
- `selftest.py` — deterministic offline tests.
- `inbox/BRIDGE-BUS-AUTO-20260929-E001.json` — safe one-shot automated post-install BRIDGE_PING.

Canonical protocol and ChatGPT project instructions were updated to prefer the GitHub command bus over the legacy DOM marker route.

## Guardrails

- WSL side is GitHub read-only: no automated push or publication.
- no live trading;
- no paid action;
- no wallet/crypto action;
- task IDs are immutable;
- command claims are durable before localhost dispatch;
- ambiguous dispatches are never automatically retried;
- ambiguous result delivery remains in `inflight` and never automatically requeues.

## Installation gate

The local machine is not considered migrated merely because these files exist on GitHub. The bootstrap must run successfully and report:

- deterministic self-tests PASS;
- wake health includes `inflight_claim:true`;
- command-bus timer active;
- qualification record written;
- automated task `BRIDGE-BUS-AUTO-20260929-E001` returns to ChatGPT.

Even after those checks, final Tier-A acceptance remains blocked pending an independent highest-intelligence Tier-A review.

## Bootstrap

From WSL, fetch and execute the canonical bootstrap from an isolated mirror. Do not checkout remote main into the dirty production working tree.

After bootstrap, normal new commands are created remotely under `control/bridge_commands/inbox/` and are picked up automatically within roughly 30 seconds.
