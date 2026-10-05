# Dashboard → ChatGPT Action Protocol

Status: CANONICAL
Version: 1
Date: 2026-10-05

## Invariant

Every Control Center/dashboard button whose purpose is to start ChatGPT work MUST
start that work in a **brand-new Prediction ChatGPT session**.

Existing Prediction chats may be used only as a browser launcher/control plane.
The dashboard action itself must never be inserted as a working user turn into an
already existing chat.

Canonical invariant:

`DASHBOARD_CHAT_ACTION_REQUIRES_NEW_SESSION`

## Flow

1. A dashboard action creates a unique immutable action/request ID and launch token.
2. The Control Center locates a fresh registered Prediction-project launcher tab.
3. A browser-control event is routed to that exact tab/consumer.
4. The userscript opens a new tab at the same Prediction project base URL.
5. The new tab consumes the launch token and submits the action prompt as its first user turn.
6. The new chat receives its automatic `SESSION-ROUTE-*` bootstrap.
7. The new chat MUST NOT dispatch local WSL/projectexecutor tasks until that bootstrap returns
   `status=PASS exit=0 kind=SESSION_ROUTE_BOOTSTRAP`.
8. After bootstrap, all local tasks from that dashboard action use the new session's own
   `route_task_id`.
9. Build-log events keep the action linked to its stable `work_item_id`.

## Fail closed

If no fresh launcher with capability `dashboard_new_session_launch_v1` is available,
the dashboard action fails with `NEW_SESSION_LAUNCHER_NOT_READY`.

There is **no fallback** to inserting the work into an existing ChatGPT session.

## Browser-control event

The existing project chat may receive:

`kind=DASHBOARD_NEW_SESSION_LAUNCH_V1`

This is browser-control metadata only. The userscript opens a new project chat and ACKs
that control event. It does not submit the event text into the existing chat.

## Safety

This mechanism changes session isolation only. It grants no additional authority for:
live trading, paid actions, wallet/fund movement, credential access, destructive Git,
privilege escalation, or WSL remote Git writes.

Action-specific protocols, such as `control/control_center/SYNC_PROTOCOL.md`, remain
binding inside the newly created session.
