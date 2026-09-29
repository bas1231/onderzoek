#!/usr/bin/env bash
set -euo pipefail

ROUTE_TASK="${1:-BRIDGE-BUS-E001}"
PROD="$HOME/prediction_research_prod"
MIRROR="$HOME/.local/share/prediction-command-bus-bootstrap"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if [ ! -d "$PROD/.git" ]; then
  echo "FOUT: production repo ontbreekt: $PROD" >&2
  exit 1
fi

REMOTE="$(git -C "$PROD" remote get-url origin)"
mkdir -p "$MIRROR"
if [ ! -d "$MIRROR/.git" ]; then
  git -C "$MIRROR" init -q
fi
git -C "$MIRROR" remote remove origin >/dev/null 2>&1 || true
git -C "$MIRROR" remote add origin "$REMOTE"
GIT_TERMINAL_PROMPT=0 git -C "$MIRROR" fetch -q --depth=1 origin main

git -C "$MIRROR" archive FETCH_HEAD control/bridge_commands | tar -x -C "$TMP"

python3 "$TMP/control/bridge_commands/selftest.py"
python3 "$TMP/control/bridge_commands/install_command_bus.py" --route-task "$ROUTE_TASK"

echo
echo "=== COMMAND BUS STATUS ==="
systemctl --user status prediction-command-bus.timer --no-pager -l || true
systemctl --user status prediction-command-bus.service --no-pager -l || true

echo
echo "=== QUALIFICATION ==="
cat "$HOME/.local/state/prediction-command-bus/qualification.json" 2>/dev/null || true

echo
echo "BOOTSTRAP KLAAR"
