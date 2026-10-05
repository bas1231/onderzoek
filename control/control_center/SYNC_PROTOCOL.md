# Prediction Control Center — One-click Sync Protocol

Status: CANONICAL

## User action

When the Control Center reports `Git-sync: Niet in sync`, the owner may press
`Sync`.

That click is explicit user authorization to start a **repository reconciliation**
within the already-approved Prediction project boundaries. It is not permission
for live trading, paid actions, wallet actions, credential access, destructive
Git operations, or autonomous WSL remote writes.

## Transport

The dashboard does not run a destructive Git command itself.

It follows `control/control_center/DASHBOARD_CHAT_ACTION_PROTOCOL.md`: every Sync click
must start the work in a brand-new Prediction ChatGPT session. An existing Prediction
chat may only act as the browser launcher that opens the new project chat.

The new chat receives `PREDICTION_CONTROL_SYNC_REQUEST_V2` as its first user turn. It
must wait for its own automatic `SESSION-ROUTE-* status=PASS exit=0` bootstrap before
dispatching any local task. There is no fallback to reusing an existing working chat.

The trigger is deduplicated for a short window so repeated clicks cannot create
parallel reconciliation attempts.

## Mandatory reconciliation rules

On receipt of `PREDICTION_CONTROL_SYNC_REQUEST_V1`, ChatGPT must:

1. Read the current canonical Prediction docs and the shared build log.
2. Continue work item `PRODUCTION-RECONCILIATION-20261005` unless a later
   canonical work item supersedes it.
3. Inspect the actual production branch, HEAD, staged/unstaged/untracked paths,
   local `main`, and fetched/canonical GitHub `main`.
4. Preserve all local committed and dirty/untracked content until it has been
   proven represented in canonical source.
5. Never use `reset --hard`, force push, destructive checkout, rebase, or
   stash/drop as a shortcut.
6. Keep WSL remote-read-only. Any GitHub remote write is performed by ChatGPT
   through the GitHub connector.
7. Use the projectexecutor's bounded production inspection/reconciliation/
   fast-forward operations for local production changes.
8. Prefer the shortest safe route:
   - if production is clean and only behind canonical `main`, perform the
     bounded safe fast-forward and verify;
   - if local commits or dirty/untracked content are not yet represented,
     represent them canonically first, prove that representation, then perform
     the bounded cleanup/switch/fast-forward;
   - if representation cannot be proven, fail closed and record the exact
     blocker.
9. Append build-log ATTEMPT/RESULT/HANDOFF events under the same work item.
10. Declare completion only after a fresh Control Center snapshot reports
    `git_sync.status == GREEN`.

## Fail closed

A one-click request is successful only when the repository really becomes
green. A delivered wake, a dispatched executor task, or a partial representation
check is not sufficient.

If safe completion is impossible, keep the repository intact and record a
BLOCKED result with the first incomplete step.
