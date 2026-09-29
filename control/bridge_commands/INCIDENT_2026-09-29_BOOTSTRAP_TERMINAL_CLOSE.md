# Incident — bootstrap closed interactive terminal (2026-09-29)

Status: open, mitigated; final Tier-A qualification pending.
Task: `TIERA-BRIDGE-COMMAND-BUS-20260929-E001`.

## What happened

The provisional install command used `git show ... | bash` to execute `control/bridge_commands/bootstrap_local.sh` directly from a pipe. The bootstrap used `set -euo pipefail`. During installation the provisional Python installer also contained lowercase identifiers (`false`) in a runtime qualification dictionary. Python compilation did not catch this because `false` is syntactically a valid name; execution later raised `NameError`, the installer entered rollback, and the bootstrap returned non-zero. In the user's terminal environment this resulted in the terminal session closing.

## Evidence / root cause

The terminal-close report followed the first automated bootstrap attempt. Review of the committed source found:

- direct pipe-to-bash execution in the operator instruction;
- `set -euo pipefail` in the old bootstrap;
- runtime-only lowercase boolean identifiers in the provisional installer qualification block.

The exact terminal-host behaviour is environment-dependent, but these controls were unsafe for an interactive recovery path and are no longer permitted.

## Corrective controls

1. `bootstrap_local.sh` is retired and is now a no-op that returns success.
2. Canonical bootstrap is `bootstrap_local_terminal_safe.sh`.
3. The safe bootstrap uses no `set -e`, no top-level `exit`, and can be sourced from the current shell.
4. Operator instructions must first run `set +e`, fetch the safe bootstrap to a local file, then `source` that file. Never use `git show ... | bash` for this bridge.
5. The safe bootstrap patches the known lowercase-boolean typo only in its temporary installer copy before execution and compiles it before mutation.
6. Failure must report `BOOTSTRAP_RC=<code>` while preserving the interactive shell.
7. Existing rollback, evidence quarantine, no-autopush, no-paid-action, no-wallet and no-live-trading guardrails remain required.

## Qualification

This incident affects Tier-A infrastructure. Functional fixes remain provisional until deterministic tests and an independent Tier-A review are complete. State: `REQUIRES_HIGH_INTELLIGENCE_REVIEW`.

Implementation model recorded for this corrective pass: GPT-5.6 Sol. Runtime reasoning-level value is unavailable, therefore it is recorded as `UNAVAILABLE_TO_RUNTIME` rather than inferred.
