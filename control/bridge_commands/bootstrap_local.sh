#!/usr/bin/env bash

# DEPRECATED / NO-OP
#
# This bootstrap was retired after the 2026-09-29 terminal-close incident.
# Do not pipe this file into bash and do not use it for installation.
# Canonical recovery/bootstrap:
#   control/bridge_commands/bootstrap_local_terminal_safe.sh
#
# Deliberately returns success so an old `git show ... | bash` invocation cannot
# trigger an interactive shell configured with errexit to close.

echo "DEPRECATED: bootstrap_local.sh voert niets meer uit."
echo "Gebruik control/bridge_commands/bootstrap_local_terminal_safe.sh"
return 0 2>/dev/null || true
