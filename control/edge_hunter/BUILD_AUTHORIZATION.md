# Edge Hunter build authorization

Every local `infrastructure` task must carry an explicit `build_authorization` object. Validation happens inside `Task.model_validate()` before the browser bridge can write or commit the task.

Research tasks do not use build authorization and remain subject to the normal research-queue rules.

## Universal autonomous build governance

`methodology/AUTONOMOUS_BUILD_PROTOCOL.md` is normative for future mutating builds. Read-only infrastructure tasks can continue using the compact authorization form below. Any infrastructure task requesting a capability outside the read-only allowlist in `control/AUTONOMOUS_BUILD_POLICY.json` is treated as **mutating** and must additionally carry a complete `build_contract` inside `build_authorization`.

The builder may not change its own objective, scope, acceptance criteria or definition of success after implementation starts. Governance is validated fail-closed by `control/edge_hunter/autonomous_build_governance.py`.

## Control-plane build

Use this only for generic safety, reliability, provenance, validation or research-infrastructure work that does not implement a candidate-specific strategy.

Read-only example:

```json
{
  "build_authorization": {
    "mode": "control_plane",
    "build_kind": "control_plane",
    "objective": "Inspect the bounded control-plane state",
    "capabilities": ["read_repository"]
  }
}
```

Mutating example:

```json
{
  "build_authorization": {
    "mode": "control_plane",
    "build_kind": "control_plane",
    "objective": "Implement one bounded control-plane change",
    "capabilities": ["read_repository", "write_repository"],
    "build_contract": {
      "build_id": "BUILD-CONTROL-001",
      "protocol_version": 1,
      "objective": "Implement one bounded control-plane change",
      "source_commit": "0123456789abcdef0123456789abcdef01234567",
      "allowed_capabilities": ["read_repository", "write_repository"],
      "allowed_paths": ["control/example"],
      "planned_paths": ["control/example"],
      "acceptance_criteria": ["Target tests pass"],
      "non_goals": ["No unrelated refactor"],
      "independent_verification": "Separate regression test or reviewer",
      "rollback_plan": "Revert the build commit",
      "cleanup_plan": "Remove temporary build-only artifacts",
      "max_attempts": 2,
      "governance_change": false,
      "safety": {
        "live_trading": false,
        "paid_actions": false,
        "wallet_actions": false
      }
    }
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

Run the issuer as an `infrastructure` task with `mode: control_plane`. If the issuer only reads/evaluates current state, no build contract is needed. If it writes a warrant or otherwise mutates the repository, the mutating control-plane task must include a build contract whose scope explicitly includes those writes.

The issuer creates a warrant only when the candidate currently passes the pre-build policy. A denied request creates no warrant.

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

If the candidate build is mutating, the same authorization also needs a valid `build_contract`. At validation time the gate re-hashes the current candidate, request, policy and build state and compares them with the stored warrant. A changed candidate, changed request, changed policy, changed build state, missing file or tampered warrant is denied.

## Forbidden capabilities

The canonical list is in `control/edge_hunter/warrant_policy.json`. It currently includes live trading/order submission, wallet/fund movement, paid actions, credential writes and venue write endpoints.

Economic status remains `NO_PROVEN_EDGE` unless the separate research evidence gates prove otherwise.
