# Research OS V1 E004 validation coordination

Status: **DO NOT MERGE / DO NOT ACTIVATE**.

E003 failed closed on 22 Sep 2026 with 8 pytest failures plus one validator packet-discovery failure. Triage found:

- one real coverage metric bug (`changed_or_new_items_reported` omitted unidentified reported changed items while uniqueness stayed strict);
- six stale test expectations after earlier fail-closed hardening (blinding audit-flag names, conflicting gate maps, evidence provenance fixture, lower-case normalized source-family output, holdout promotion fixture);
- one E003 validator bug: packet discovery inspected absolute path parts, so the outer `.../experiments/bridge/worktrees/...` path caused every repository JSON file to be excluded.

The Research-OS integration branch now contains the corrected runtime metric and aligned regression fixtures. E004 fixes packet discovery by filtering only repository-relative path parts.

Canonical validation route:

1. Build `ai/research-os-v1-frozen-validation` from the current `main` plus only the frozen Research-OS subtrees/docs.
2. Require 0 commits behind `main` and no diff outside the allowed Research-OS scope.
3. Run `control/jobs/validate_research_os_frozen_e004.py` locally in an isolated worktree.
4. Require Research-OS pytest, all three validators, full repo pytest, real read-only shadow CLI, tracked-mutation check, and economic default `NO_PROVEN_EDGE` all to pass.

No paid actions, live trading, wallet actions, credential export, or active factory mutation are authorized.
