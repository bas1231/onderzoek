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

The visual theme follows the dark navy / magenta / cyan design language used by
the FG-assistant.

## Canonical edge lifecycle displayed

`Scout -> selectie -> GPT-5.6 Sol-opzet -> GPT-6 Astra pre-build review ->
GPT-5.6 Sol-build -> GPT-6 Astra post-build code-review -> tests en meting ->
supervisor -> rapportage`

The dashboard is observability only; it never relaxes
`NO_TEST_OR_MEASUREMENT_BEFORE_ASTRA_POSTBUILD_APPROVAL`.
