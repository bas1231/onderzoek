# Edge Hunter build authorization

Every local `infrastructure` task must now carry an explicit `build_authorization` object. Validation happens inside `Task.model_validate()` before the browser bridge can write or commit the task.

Research tasks do not use build authorization and remain subject to the normal research-queue rules.

## Control-plane build

Use this only for generic safety, reliability, provenance, validation or research-infrastructure work that does not implement a candidate-specific strategy.

```json
{
  "build_authorization": {
    "mode": "control_plane",
    "build_kind": "control_plane",
    "objective": "Describe the bounded control-plane change",
    "capabilities": ["read_repository", "write_research_artifact"]
  }
}
```

Control-plane authorization still fails closed when the build state is frozen or when a forbidden capability is requested.

## Issuing a candidate warrant

Write a JSON request under `experiments/bridge/warrant_requests/` that follows `control/edge_hunter/warrant_request_schema.json`.

Example request:

```json
{
  "candidate_id": "PAYOFF-IDENTITY-MINING-V1",
  "build_kind": "offline_analysis",
  "objective": "Build a bounded offline equivalence analyser",
  "capabilities": ["read_repository"]
}
```

Run the issuer as an `infrastructure` task with `mode: control_plane`:

```json
{
  "operation": "python",
  "command": [
    ".venv/bin/python",
    "control/jobs/issue_prebuild_warrant.py",
    "experiments/bridge/warrant_requests/<request>.json"
  ],
  "build_authorization": {
    "mode": "control_plane",
    "build_kind": "control_plane",
    "objective": "Evaluate and issue one bounded candidate pre-build warrant",
    "capabilities": ["read_repository", "write_warrant", "stage_warrant"]
  }
}
```

The issuer creates a warrant only when the candidate currently passes the pre-build policy. The exact warrant file is then staged with `git add`; the normal executor result commit therefore preserves the warrant itself in Git provenance. A denied request creates no warrant.

## Candidate-specific build

Candidate code requires a previously issued pre-build warrant under `knowledge/warrants/` and must use the exact same build kind, objective and capability set that was evaluated by that warrant.

```json
{
  "build_authorization": {
    "mode": "candidate",
    "build_kind": "offline_analysis",
    "objective": "Exact objective covered by the warrant",
    "capabilities": ["read_repository"],
    "warrant_ref": "knowledge/warrants/<warrant>.json"
  }
}
```

At validation time the gate re-hashes the current candidate, request, policy and build state and compares them with the stored warrant. A changed candidate, changed request, changed policy, changed build state, missing file or tampered warrant is denied.

## Forbidden capabilities

The canonical list is in `control/edge_hunter/warrant_policy.json`. It currently includes live trading/order submission, wallet/fund movement, paid actions, credential writes and venue write endpoints.

Economic status remains `NO_PROVEN_EDGE` unless the separate research evidence gates prove otherwise.
