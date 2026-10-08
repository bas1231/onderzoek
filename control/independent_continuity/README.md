# Independent Continuity Observer — v1

Status: **implemented source; NOT deployed as a background service; not an auto-resume agent**.

## Non-negotiable separation

This component is in `control/independent_continuity/` and imports only the
Python standard library. It **never** imports, patches, installs into or
controls the GitHub command bus, poller/router/receiver, project executor,
wake bridge, browser extension or model routing. It makes no GitHub API or
network calls, dispatches no tasks, modifies no approval gates, and cannot
submit a ChatGPT turn. Existing infrastructure has an explicit owner freeze.

The input is a **read-only local snapshot** of
`control/build_log/events/*.json`. The output is a deterministic immutable
incident/proposal file in a separate directory chosen by the operator.

## Run a single independent scan

```bash
python3 -m control.independent_continuity.observer \
  --events-dir control/build_log/events \
  --proposals-dir /tmp/prediction-independent-continuity \
  --stale-minutes 30 --once
```

Continuous local observer (an independent process, no WSL service installed):

```bash
python3 -m control.independent_continuity.observer \
  --events-dir control/build_log/events \
  --proposals-dir /tmp/prediction-independent-continuity \
  --stale-minutes 30 --interval-seconds 60
```

Use only a fresh, authorized repository snapshot; the observer does **not**
refresh Git itself. A stale checkout produces a stale **observation**, not an
authoritative claim about current execution. All classifications mean
"investigate", not "restart".

## Classification / recovery policy

- `UNVERIFIED_TASK_OR_DISPATCH`: no durable task result in build log. Never
  repeat an immutable task; first verify remote command claim, WSL executor
  state, receipt, and exact session routing.
- `FAILED_NEEDS_DIAGNOSIS`: investigate the first incomplete operation; fix
  narrowly under standard authorization.
- `HANDOFF_REVIEW_REQUIRED`: a PASS left declared work. Read the next step,
  verify it's still current, then check model/gate provenance before continuing.
- `MISSING_NEXT_STEP`: don't invent missing procedure.
- `STALE_NEEDS_REVIEW`: uncertain state; audit, don't assume.
- `CLOCK_OR_SNAPSHOT_ERROR`: suspicious timing; fail closed.
- Invalid event syntax, identity or schema: `INPUT_INVALID`, **no proposals**.
- Latest `DONE` or `BLOCKED` ledger state: no recovery proposal.
- A merely recent NOTE does not conceal a stale substantive task.

Reports are named by a deterministic SHA-256-derived ID and created with
`O_EXCL`: they are never silently replaced or duplicated. They contain
`execution_authorized:false` and `automatic_resubmission:false`.

## The crucial missing piece for *true* automatic continuation

A separate authorized **actuator** would need a proven way to invoke a **fresh**
ChatGPT session with its own routing/provenance, assess the actual immutable
evidence, and choose exactly one permitted next action. A passive observer
cannot create a ChatGPT assistant response when the original conversation
stops. Do not mislabel these reports as recovered builds.

Such an actuator must not create an alternate WSL transport, re-execute an
ambiguous task, amend bridge/executor/runtime source, bypass Sol/Astra's
version-bound reviews, perform unapproved paid actions, or permit trading.
Deployment or browser-control integration is a **separate acceptance step**,
not included in v1.

## Acceptance

Run:
```bash
python3 -m unittest discover -s tests/independent_continuity -p 'test_*.py' -v
```

Regression coverage includes missed responses, reported PASS but incomplete
work, failures, terminal states, missing next steps, timing, idempotence,
collisions and malformed/untrusted input.

No services or timers are installed by this commit.

## Standalone coordinator v2 (source present; activation gated)

The companion files `coordinator.py`, `snapshot.py` and `runner.py`
add a standalone recovery coordinator. They do NOT modify the installed command
bus, project executor, wake bridge, browser extension, existing unit files,
ports, tokens, ACK handling or routing semantics.

- `snapshot.py` loads a pinned freshly fetched `FETCH_HEAD` Git tree with
  **local read-only** `git rev-parse` and `git archive`. It NEVER trusts the
  mirror's possibly stale checked-out files, runs `git fetch`, pushes or
  checks out. A stale fetch, malformed event or unsafe archive fails closed.
- `runner.py` periodically runs the observer from an isolated temp snapshot.
  Its default `observe` mode produces only local diagnostic files, even
  if the browser is closed; no wake bridge writes.
- The separate `coordinator.py` may **only after explicit `mode: emit`**
  publish the already-installed `DASHBOARD_NEW_SESSION_LAUNCH_V1` message
  contract. It is a producer using the existing dashboard launcher, NOT a
  replacement bridge transport. It never creates a task or decides a model
  gate. A new chat must obtain its OWN session route.
- Emission is blocked without an explicitly allowlisted `work_item_id`, a
  fresh Git snapshot (max 180 seconds old), a current unchanged ledger-derived
  proposal, a proven matching active Prediction browser launcher (max 180
  seconds old), and an unclaimed recovery ID. Writes are O_EXCL; a partial
  launch is ambiguous and never silently retried. The launcher is capped at
  three requests per work item per day and 30-minute minimum interval.
- Recovery text is a forensic request generated from stable IDs only; no
  untrusted `next_action` content is injected into it. It authorizes no build,
  paid activity, trading, wallets or bypass of Astra approvals.

The sample `scope.observe.json` monitors only
`A2Z-SYSTEMTEST-20261005` after 90 minutes of no substantive ledger
progress. It deliberately has `mode: observe` and all monetary/trading
flags false.

The new `prediction-independent-continuity.service` and
`prediction-independent-continuity.timer` are **separate** user units, not
modifications to the established bridge/executor services. Their source
files are inert until explicitly installed. No bridge/runtime files are
overwritten or removed by the independent component.

### Deployment gates

1. Standalone unit and snapshot regression tests PASS against exact pinned
   source.
2. The new code/config/user-unit files are installed only into their own
   allowlisted directories by a bounded projectexecutor install task.
3. The separate observation service is tested in `mode: observe`.
4. **Only after separate activation evidence**, and without changes to the
   frozen bridge/executor, may `mode: emit` be considered. A dashboard
   launch is only a queued request, not proof that a new ChatGPT session
   started or completed its work.

Neither E001/E002 observation PASS alone nor static coordinator tests satisfy
the full end-to-end self-recovery acceptance criterion.
