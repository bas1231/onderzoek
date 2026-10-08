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
