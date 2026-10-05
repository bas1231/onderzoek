# Prediction Build Log Protocol

Status: CANONICAL
Purpose: prevent duplicate work, circular debugging, and loss of context across simultaneous ChatGPT sessions.

## Principle

The build log is an append-only shared work ledger.

- One real objective = one stable `work_item_id`.
- Every attempt uses a fresh immutable task ID, but remains linked to the same work item.
- Never overwrite an earlier event.
- A task-level `PASS` does not automatically mean the work item is `DONE`.
- A failed attempt records the first incomplete step, the observed cause, and the exact next action.
- A new session continues an existing open work item instead of starting the same investigation from scratch.

Canonical event location:

`control/build_log/events/<EVENT_ID>.json`

Schema:

`control/build_log/SCHEMA_V1.json`

## Required workflow for project work

Before starting a substantial Prediction build, diagnosis, repair, or qualification:

1. Read the open build-log work items.
2. Decide whether the requested work already belongs to an existing `work_item_id`.
3. If it does, continue that work item. Do not create a parallel duplicate.
4. If it is genuinely new, create a new work item with a `PLAN` event.
5. Before dispatching a local task, add an `ATTEMPT` or `PLAN` event containing the exact goal and first expected verification.
6. After the task result returns to the intended chat, add a `RESULT` event with:
   - PASS / FAIL / BLOCKED;
   - what was actually proven;
   - why it succeeded or failed;
   - the first incomplete step;
   - the next action;
   - task ID and evidence references.
7. If the objective is completely satisfied, close the work item with `work_item_status: DONE`.
8. If another session should continue, add a `HANDOFF` event that names the first incomplete step.

## Anti-circle rule

Before repeating an experiment, diagnostic, repair, or verification, inspect the existing timeline for that work item.

A repeated action is justified only when at least one of these is true:

- an earlier attempt failed before reaching that action;
- the implementation or evidence changed materially;
- the repeated step is an explicit regression check;
- the earlier evidence was ambiguous or incomplete.

Otherwise continue at the first incomplete step instead of replaying earlier successful work.

## Result semantics

`work_item_status` tracks the objective:

- `OPEN`: known work remains.
- `IN_PROGRESS`: actively being worked.
- `BLOCKED`: cannot proceed without a missing dependency/approval/capability.
- `DONE`: the complete objective and its acceptance criteria are satisfied.

`outcome` tracks one event or attempt:

- `PLANNED`
- `STARTED`
- `PASS`
- `FAIL`
- `BLOCKED`
- `INFO`
- `SUPERSEDED`

A `RESULT/PASS` may leave the work item `OPEN` or `IN_PROGRESS` if more acceptance criteria remain.

## Cross-session requirements

Every event should include the current `session_route_task_id` when known. This gives the dashboard a multi-session audit trail without using the route as the identity of the work itself.

All ChatGPT sessions working on Prediction must treat the ledger as shared state. GitHub is the canonical remote write location. WSL remains GitHub read-only.

## Dashboard interpretation

The Control Center groups immutable events by `work_item_id` and shows:

- what still needs to happen;
- current work-item status;
- every attempt and result;
- why an attempt succeeded or failed;
- the first incomplete step;
- the next action;
- session route, task IDs, commits and evidence;
- duplicate/open work so circular work is visible.

Historical command-bus/project-executor tasks remain forensic evidence, but they do not replace the structured build ledger.


## Session assignment / drift detection

A Prediction session may have an explicit assignment scope in any immutable build-log event via:

- `session_assignment_scope.instruction`: the human-readable assignment for that session;
- `session_assignment_scope.allowed_work_item_ids`: the work-items explicitly authorized in that session.

A supporting/dependency work-item may declare `supports_work_item_id` so bounded prerequisite work does not count as session drift.

Control Center drift detection is deterministic and evidence-based:
- it only evaluates active tasks with a known `session_route_task_id`;
- it maps each active task to the build-log work-item that names that task ID;
- an active task outside the current session assignment scope is flagged unless its work-item explicitly supports an allowed work-item;
- an active task with no build-log work-item mapping is flagged as untracked session work;
- no opaque LLM similarity score is used as the sole trigger.

When the user explicitly expands or changes a session's assignment, append a new immutable NOTE event with the new `session_assignment_scope`. The latest scope event for that route is authoritative.
