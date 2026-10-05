# Prediction Control Center

Local owner cockpit for the Prediction research system.

## Goals

- one view across all ChatGPT session routes;
- every candidate/idea remains inspectable from discovery to terminal decision;
- every historical research run remains available, including scout/agent packet artifacts;
- errors, bottlenecks, task latency and successful components are visible;
- existing historical candidates and manual scout seeds are indexed automatically;
- legacy research documents are listed for later re-evaluation;
- a re-research request never overwrites history: it creates an immutable
  `PREDICTION_RESEARCH_REVIVE_REQUEST_V1` linked to the original candidate.

## Data sources

The server is a local projection over existing sources of truth. It does not create
a second research database.

It reads primarily:

- `knowledge/candidates/*.json`
- `knowledge/manual_scout_seeds/*.md`
- `knowledge/runs/**/*.json`
- `knowledge/runs/agent_packets/**`
- `knowledge/research/*.md` and related legacy research folders
- `~/.local/state/prediction-command-bus/tasks/*.json`
- `~/.local/state/prediction-project-executor/*.json`

The dashboard groups tasks by `route_task_id`, so concurrent ChatGPT sessions are
visible together without changing same-chat result routing.

## Safety

The HTTP server binds to loopback only (default `127.0.0.1:8770`).

The dashboard does not submit orders, move funds, invoke paid APIs or modify
candidate history. All economic safety flags remain false.

The only write endpoint is `POST /api/revive`. It creates an immutable local
request under:

`~/.local/state/prediction-project-executor/control-center/revive_requests/`

That request is *not* an execution authorization. A later controlled research
ingress may consume it by creating a new attempt under the then-current governed
lifecycle. The old candidate and evidence remain unchanged.

## UI

Open:

`http://127.0.0.1:8770`

Main areas:

- Overview
- Live (all session routes)
- Ideas / Idea Journey
- Runs (including scout/agent artifacts)
- Errors
- Performance
- History / revive requests
- System / raw task state

A persistent A→Z lifecycle strip is visible above every page. Its evidence-bound
status comes from `control/control_center/lifecycle_status.json`. Green means a
component is operationally working, cyan means a targeted gate/test has passed,
and amber means the step is present or specified but still needs proof inside one
complete current A→Z run. The global status remains `NOT_PROVEN` until that full
run is actually evidenced.

The visual theme follows the dark navy / magenta / cyan design language used by
the FG-assistant.

## One-click repository sync

When Git-sync is red, the UI shows a `Sync` button. The button does not run
Git directly. It creates a bounded local sync request and queues
`PREDICTION_CONTROL_SYNC_REQUEST_V1` to the most recently proven ChatGPT
Prediction route.

The receiving ChatGPT session follows
`control/control_center/SYNC_PROTOCOL.md`: preserve local work, use GitHub
remote writes only through the ChatGPT connector, use the projectexecutor for
bounded local reconciliation, and never use reset/force/rebase/stash-discard
shortcuts. Repeated clicks within the active request window are deduplicated.

Completion means a fresh dashboard snapshot reports `git_sync.status == GREEN`.

## Shared build log

The `Logboek` page is a projection of immutable events under:

`control/build_log/events/*.json`

The canonical operating rules are in `control/build_log/PROTOCOL.md`. A stable
`work_item_id` survives retries and ChatGPT-session handoffs; individual executor
attempts keep fresh task IDs. The dashboard shows the current objective status,
why attempts passed or failed, the first incomplete step, next action, related
session routes/tasks/commits, and the complete event timeline.

For multi-session freshness the server prefers the read-only command-bus
`FETCH_HEAD` mirror, then the project-executor mirror, then the production
working tree. Events are immutable and deduplicated by `event_id`; the dashboard
does not write GitHub.

Exact duplicate open objectives are flagged as an anti-circle warning.

## Canonical edge lifecycle displayed

`Scout -> selectie -> GPT-5.6 Sol-opzet -> GPT-6 Astra pre-build review ->
GPT-5.6 Sol-build -> GPT-6 Astra post-build code-review -> tests en meting ->
supervisor -> rapportage`

The dashboard is observability only; it never relaxes
`NO_TEST_OR_MEASUREMENT_BEFORE_ASTRA_POSTBUILD_APPROVAL`.
