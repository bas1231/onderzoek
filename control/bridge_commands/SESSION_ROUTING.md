# Prediction Command Bus — Session Routing

Status: canonical routing rule for multi-session use.
Updated: 2026-09-29 after `DEV-PRED-SESSION-BOOTSTRAP-INSTALL-20260929-E010` PASS.

## Problem addressed

The command bus supports a global pinned route in `~/.config/prediction-command-bus/route.json`. That route is convenient for a single control chat, but it is not sufficient as the default addressing mechanism when multiple Prediction chats/sessions can issue commands concurrently. A task may execute correctly while its result is delivered to a different previously pinned chat.

A second issue existed in the first bootstrap of a brand-new chat: the old procedure depended on a visible assistant DOM marker or manual menu ping. That legacy marker path had already proven unreliable.

## Canonical rule for new sessions

Every Prediction session that expects local results back in that same chat must establish and then reuse a **session-specific route task ID**.

1. If this chat already has a task whose result demonstrably returned successfully here, reuse that task ID as `route_task_id`.
2. For a brand-new chat, do **not** emit a visible `[[PREDICTION_CMD:...]]` marker as the normal bootstrap mechanism.
3. The installed wake bridge now bootstraps the route automatically from the existing browser `/next` poll, which already carries the stable `chat_id` and `consumer_id`.
4. A new chat with no proven routed result receives an idempotent message of the form:

   `NIGHTSHIFT_WSL_RESULT_V1 task=SESSION-ROUTE-... status=PASS exit=0 kind=SESSION_ROUTE_BOOTSTRAP`

5. Once that message has appeared in the same chat, use its `SESSION-ROUTE-...` task ID as `route_task_id` for subsequent GitHub command-bus tasks in that session.
6. Do not normally use `route_task_id: null` for build/test/diagnostic tasks when more than one Prediction session may be active.
7. `route_task_id: null` is reserved for an intentionally pinned single control route or explicit infrastructure diagnostics.

The old legacy/menu ping remains diagnostic fallback only. It is no longer the canonical new-session bootstrap.

## Why the automatic bootstrap is safe

The bootstrap does not execute a project command. It creates only a chat-scoped route record and a small idempotent control result. Normal command execution remains durable and at-most-once.

The route task ID is deterministic for a chat (`SESSION-ROUTE-` plus a hash of the stable chat ID), so repeated wake polling does not create different logical routes for the same chat. Duplicate OUTBOX announcements are suppressed. If delivery became ambiguous in `inflight`, the idempotent bootstrap announcement may be re-announced only after the bounded delay implemented by the wake wrapper. This retry rule applies only to the route announcement, never to command execution.

Runtime implementation:

`control/tampermonkey_multichat/bridge_server_session_bootstrap.py`

Installed server version after E010:

`PredictionChatWake/0.9-session-bootstrap`

## Example normal command

```json
{
  "schema": "PREDICTION_BRIDGE_COMMAND_V1",
  "task_id": "DEV-EXAMPLE-E001",
  "action": "SIX_AI_HEALTH",
  "route_task_id": "SESSION-ROUTE-<THIS_CHAT>",
  "live_trading": false,
  "paid_actions": false,
  "wallet_actions": false,
  "intelligence_tier": "C",
  "issuer": {
    "model": "<actual model>",
    "reasoning_level": "UNAVAILABLE_TO_RUNTIME"
  },
  "created_at_utc": "<UTC>"
}
```

## Delivery semantics

A command being `DISPATCHED` only proves local router acceptance. It does not prove that the result reached the intended chat. Success requires the same task ID to return through the wake/result bridge with the expected status/assertions.

Because command claims are at-most-once, an already-claimed command task is never reused to repair delivery. If delivery is missing or ambiguous, diagnose the existing state and create a **fresh command task ID** with the explicit session route.

The automatic `SESSION_ROUTE-*` announcement is not a command execution and is deliberately idempotent; its bounded re-announcement does not relax command at-most-once semantics.

## Concurrency

Different Prediction sessions may run concurrently as long as each command carries its own valid `route_task_id`. Do not solve concurrent routing by repeatedly overwriting the global pinned route; explicit per-command routing is the canonical multi-session mechanism.

## Evidence

Before automatic bootstrap, the pair below proved explicit same-chat routing once a route existed:

- `TM-PING-1790690332005` -> PASS, exit 0
- `BRIDGE-COMMAND-BUS-CURRENT-ROUTE-E008` -> PASS, exit 0

Automatic bootstrap build/install then returned through the same proven command bus:

- `DEV-PRED-SESSION-BOOTSTRAP-INSTALL-20260929-E010` -> PASS, exit 0

E010 ran the session-bootstrap regression suite, compile checks, installed the new wake wrapper, restarted `prediction-chat-wake.service`, required it to be active, and executed an installed-runtime canary. A final acceptance test for the product behaviour is a genuinely brand-new Prediction chat receiving its own `SESSION-ROUTE-*` PASS automatically; record that evidence in `CURRENT_STATE.md` when observed.

## Safety

Routing changes do not relax any existing guardrail. Live trading, paid actions, wallet/crypto actions, credential writes and autonomous WSL GitHub writes remain governed separately and fail closed.
