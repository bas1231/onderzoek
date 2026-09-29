# Prediction Project Instructions — Session routing addendum

Paste or merge this into the Prediction Project instructions.

---

## SESSION-SPECIFIC BRIDGE ROUTING

Prediction can have multiple ChatGPT sessions active at the same time. Do not rely blindly on the shared global pinned command-bus route for normal build/test/diagnostic tasks.

For every session that expects WSL results back in the same chat:

- establish a `session_route_task_id`: a task from THIS chat whose result is known to have returned successfully to THIS chat;
- set `route_task_id` to that value on every subsequent command-bus task from this session;
- do not normally use `route_task_id: null` when multiple Prediction sessions may be active;
- use `route_task_id: null` only for an intentionally pinned single control route or initial route bootstrap;
- if a new chat has no route, bootstrap one once through the documented fallback/menu route, verify the result returned to this chat, then use that bootstrap task ID explicitly for the rest of the session.

A command marked `DISPATCHED` is not enough to claim success. Require the same task ID to return to this chat with the expected `status`, `exit` and task-specific assertions.

Task IDs remain immutable and at-most-once. If a result is missing, do not redispatch or mutate the old task. Inspect its state and create a fresh task with a fresh task ID and the explicit `session_route_task_id`.

Canonical details: `control/bridge_commands/SESSION_ROUTING.md` and `control/NEW_SESSION_LOCAL_EXECUTION.md`.

---
