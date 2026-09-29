# Prediction Command Bus — Session Routing

Status: canonical routing rule for multi-session use.

## Problem addressed

The command bus supports a global pinned route in `~/.config/prediction-command-bus/route.json`. That route is convenient for a single control chat, but it is not sufficient as the default addressing mechanism when multiple Prediction chats/sessions can issue commands concurrently. A task may execute correctly while its result is delivered to a different previously pinned chat.

## Rule for new sessions

Every Prediction session that expects local results back in that same chat must establish and then reuse a **session-specific route task ID**.

1. Find a task from the current chat whose result is known to have returned successfully to this chat.
2. Use that task ID as `route_task_id` on every subsequent command from this session.
3. Do not normally use `route_task_id: null` for build/test/diagnostic tasks when more than one Prediction session may be active.
4. `route_task_id: null` is reserved for an intentionally pinned single control route or initial route bootstrap.
5. If a brand-new chat has no route yet, establish one once using the documented legacy/menu bootstrap path, verify that the result returned to this chat, and then use that bootstrap task ID explicitly thereafter.

## Example

```json
{
  "schema": "PREDICTION_BRIDGE_COMMAND_V1",
  "task_id": "DEV-EXAMPLE-E001",
  "action": "SIX_AI_HEALTH",
  "route_task_id": "<KNOWN_GOOD_TASK_FROM_THIS_CHAT>",
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

Because command claims are at-most-once, an already-claimed task is never reused to repair delivery. If delivery is missing or ambiguous, diagnose the existing state and create a **fresh task ID** with an explicit session route.

## Concurrency

Different Prediction sessions may run concurrently as long as each command carries its own valid `route_task_id`. Do not solve concurrent routing by repeatedly overwriting the global pinned route; explicit per-command routing is the canonical multi-session mechanism.

## Safety

Routing changes do not relax any existing guardrail. Live trading, paid actions, wallet/crypto actions, credential writes and autonomous WSL GitHub writes remain governed separately and fail closed.
