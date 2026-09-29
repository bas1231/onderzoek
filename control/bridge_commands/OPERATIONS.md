# Prediction GitHub Command Bus — Operations

Status: provisional Tier-A infrastructure (`REQUIRES_HIGH_INTELLIGENCE_REVIEW`)

Task: `TIERA-BRIDGE-COMMAND-BUS-20260929-E001`

## Purpose

This is the primary assistant -> WSL command transport for Prediction. It was introduced after repeated failures in the ChatGPT DOM command scanner. The transport deliberately removes ChatGPT DOM parsing from the command path.

Command path:

`ChatGPT assistant -> private GitHub repo -> local read-only poller -> localhost:8767 router -> localhost:8766 receiver -> WSL`

Result path:

`WSL -> localhost:8765 wake bridge -> ChatGPT`

The result queue uses fail-closed `outbox -> inflight -> sent` semantics once the inflight runtime patch is installed. Leasing an event moves it atomically to `inflight` before it is returned to the browser. An ambiguous browser delivery therefore cannot block newer results and is never automatically resent.

## Hard safety rules

- WSL command-bus polling is **read-only against GitHub**. It may fetch, but it must never push, publish, merge or mutate the remote.
- `live_trading`, `paid_actions` and `wallet_actions` must all be explicit `false`; otherwise the poller rejects the command before dispatch.
- Existing no-autopush, no-paid-action, no-wallet and no-live-trading guardrails remain in force.
- Every task ID is immutable. Never edit/reuse a task ID. If a command is wrong, create a new task ID.
- The poller records a durable local claim **before** POSTing to localhost. A transport exception after that point is `AMBIGUOUS` and is never retried automatically.
- Deterministic transport/provenance checks are Tier C and do not depend on LLM judgment.
- Critical infrastructure remains provisional until deterministic tests, provenance checks and an independent Tier-A review are green.

## How a ChatGPT session sends a command

Use the GitHub connector to create exactly one new file:

`control/bridge_commands/inbox/<TASK_ID>.json`

Do not modify an existing command file. The file must follow `COMMAND_SCHEMA_V1.json`.

Minimal example:

```json
{
  "schema": "PREDICTION_BRIDGE_COMMAND_V1",
  "task_id": "BRIDGE-EXAMPLE-20260929-E001",
  "action": "BRIDGE_PING",
  "created_at_utc": "2026-09-29T10:30:00Z",
  "route_task_id": null,
  "live_trading": false,
  "paid_actions": false,
  "wallet_actions": false,
  "intelligence_tier": "C",
  "issuer": {
    "model": "GPT-5.6 Sol",
    "reasoning_level": "UNAVAILABLE_TO_RUNTIME"
  }
}
```

`route_task_id` is optional. When null, the poller uses the locally pinned control route in `~/.config/prediction-command-bus/route.json`. To route a result to a different ChatGPT chat, set `route_task_id` to a task that already has a valid local route for that chat. If a brand-new chat has no route yet, use the legacy bridge/menu only once to establish a route, then pin that task as the new control route.

## Local poller

Installed runtime:

- program: `~/.local/share/prediction-command-bus/command_bus_poller.py`
- read-only mirror: `~/.local/share/prediction-command-bus/repo`
- durable task state: `~/.local/state/prediction-command-bus/tasks/`
- incidents: `~/.local/state/prediction-command-bus/incidents/`
- pinned route: `~/.config/prediction-command-bus/route.json`
- service: `prediction-command-bus.service`
- timer: `prediction-command-bus.timer`

The timer polls every 30 seconds. It does not touch the working tree at `~/prediction_research_prod`.

Useful checks:

```bash
systemctl --user status prediction-command-bus.timer --no-pager -l
systemctl --user status prediction-command-bus.service --no-pager -l
journalctl --user -u prediction-command-bus.service -n 100 --no-pager
cat ~/.config/prediction-command-bus/route.json
```

## Durable at-most-once rule

For each task the poller stores the SHA-256 of the exact remote command bytes plus the fetched remote commit SHA. Before dispatch it atomically writes a local `CLAIMED` record. Outcomes are then one of:

- `DISPATCHED`: localhost returned a confirmed 2xx response;
- `REJECTED`: deterministic validation or localhost explicitly rejected the command;
- `AMBIGUOUS`: dispatch may or may not have reached the local receiver; never retry automatically;
- `BLOCKED_ROUTE`: no valid route was available; no dispatch occurred.

If the same task ID later appears with different content, the poller raises `TASK_ID_CONTENT_CONFLICT` and does not dispatch it.

## Result queue

After the inflight patch is installed:

- `outbox/` = not yet leased;
- `inflight/` = leased exactly once, browser delivery may be delivered or ambiguous;
- `sent/` = browser ACK confirmed;
- `quarantine/` = preserved legacy/ambiguous evidence, never treated as sent.

A result is moved `outbox -> inflight` atomically before `/next` returns it. There is no automatic `inflight -> outbox` retry. Replay is a deliberate/manual operation only.

## Bootstrap / reinstall

The canonical installer is `control/bridge_commands/install_command_bus.py`. Run it from a dedicated fetched copy, never by checking out files into the dirty production working tree.

Current initial control route was proven by task `BRIDGE-BUS-E001` on 2026-09-29. Installation should use that task as `--route-task` until a newer route is deliberately pinned.

## Evidence from 2026-09-29

`BRIDGE-BUS-E001` proved the full path:

- assistant created the private GitHub command file;
- WSL fetched it read-only;
- router returned HTTP 200 and `exit_code: 0`;
- local outbox contained the matching `RESULT_READY` with `BRIDGE_PONG`;
- after stale queue blockers were quarantined, ChatGPT received `NIGHTSHIFT_WSL_RESULT_V1 task=BRIDGE-BUS-E001 status=PASS exit=0`.

This is functional evidence, not final Tier-A qualification.

## New-session rule

A new Prediction chat/session must read this file first and then `control/tampermonkey_multichat/PROTOCOL.md`. For normal commands prefer this GitHub command bus. Use visible `[[PREDICTION_CMD:...]]` only as a diagnostic/route-bootstrap fallback, not as the primary command transport.
