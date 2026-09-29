# Prediction Project Instructions — Local execution block

Paste or merge this block into the ChatGPT Prediction Project instructions.

---

## LOCAL EXECUTION / WSL

Prediction has an installed GitHub command bus and a capability-scoped project executor. New sessions must use them instead of asking the user to paste normal build/test/diagnostic commands into WSL.

At the start of any session that needs local execution, first read the canonical Git files in this order:

1. `control/bridge_commands/CURRENT_STATE.md`
2. `control/NEW_SESSION_LOCAL_EXECUTION.md`
3. `control/bridge_commands/OPERATIONS.md`
4. `control/PROJECT_EXECUTOR.md`
5. `control/tampermonkey_multichat/PROTOCOL.md`
6. `control/tampermonkey_multichat/CHATGPT_PROJECT_INSTRUCTIONS.md`

Canonical primary path:

`ChatGPT -> private GitHub -> read-only WSL poller -> local receiver -> project executor -> wake/result bridge -> ChatGPT`

For ordinary local commands, create a fresh immutable command under:

`control/bridge_commands/inbox/<TASK_ID>.json`

For project code/build/test/management work, use the capability-scoped executor:

- create immutable `control/project_tasks/<TASK_ID>.json` in `bas1231/onderzoek`;
- pin a real `source_commit`;
- declare only necessary capabilities/operations;
- create the matching `bas1231/fg-assistent/dev_tasks/<TASK_ID>.json` transport manifest that invokes `project_task_executor.py <TASK_ID>`;
- dispatch the same task ID through the command bus using the current DEV transport adapter documented in `control/NEW_SESSION_LOCAL_EXECUTION.md`;
- require the returned same-task result to be `status=PASS exit=0` before claiming success.

The executor is operational for normal Prediction work. Proven capabilities include isolated worktree writes, repository-owned Python execution, tests, local Git commits, bounded Prediction runtime installs, `prediction-*` user-service management/status, and Prediction journal reads.

Do not create an unrestricted shell backdoor. Existing hard boundaries remain: no sudo/root, no autonomous WSL GitHub push, no credential access/write, no unrestricted external network from project code, no live trades/orders, no wallet/crypto/fund movement, and no paid API/cloud/subscription action without explicit approval for that specific cost.

Task IDs are immutable and never reused. WSL remains GitHub read-only; remote repo writes are performed by ChatGPT through the GitHub connector. Ambiguous dispatches/results are not silently retried.

If a local task fails, diagnose through the same command bus first: inspect task/receipt/state, classify the first incomplete stage, make one targeted fix, add a regression test where appropriate, and rerun under a fresh task ID. Ask the user for manual terminal intervention only when the command bus itself is unavailable and cannot be repaired autonomously, physical/KYC/login interaction is required, or a specific cost/trade/wallet approval is required.

For Tier A work, continue to follow the project's intelligence-routing and governance rules. Operational use of the bridge/executor does not by itself mean the formal independent Tier-A review record is complete.

---
