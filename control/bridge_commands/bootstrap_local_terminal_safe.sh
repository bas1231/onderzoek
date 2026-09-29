#!/usr/bin/env bash

# Terminal-safe bootstrap for the Prediction command bus.
# Intentionally: no `set -e`, no `exit`, no pipe-to-bash requirement.
# All failures return from main so a sourced interactive shell remains open.

main() {
    ROUTE_TASK="${1:-BRIDGE-BUS-E001}"
    PROD="$HOME/prediction_research_prod"
    MIRROR="$HOME/.local/share/prediction-command-bus-bootstrap-safe"
    TMP="$(mktemp -d)" || { echo "FOUT: mktemp"; return 1; }

    cleanup() { rm -rf "$TMP" >/dev/null 2>&1 || true; }
    trap cleanup RETURN

    echo "=== PREDICTION COMMAND BUS SAFE BOOTSTRAP ==="

    if [ ! -d "$PROD/.git" ]; then
        echo "FOUT: production repo ontbreekt: $PROD"
        return 1
    fi

    REMOTE="$(git -C "$PROD" remote get-url origin 2>/dev/null)"
    if [ -z "$REMOTE" ]; then
        echo "FOUT: origin URL ontbreekt"
        return 1
    fi

    mkdir -p "$MIRROR" || { echo "FOUT: mirror map"; return 1; }
    if [ ! -d "$MIRROR/.git" ]; then
        git -C "$MIRROR" init -q || { echo "FOUT: mirror init"; return 1; }
    fi
    git -C "$MIRROR" remote remove origin >/dev/null 2>&1 || true
    git -C "$MIRROR" remote add origin "$REMOTE" || { echo "FOUT: remote add"; return 1; }

    echo "1/6 remote fetch (read-only)"
    GIT_TERMINAL_PROMPT=0 git -C "$MIRROR" fetch -q --depth=1 origin main || {
        echo "FOUT: remote fetch"
        return 1
    }

    git -C "$MIRROR" archive FETCH_HEAD control/bridge_commands | tar -x -C "$TMP" || {
        echo "FOUT: bridge_commands extract"
        return 1
    }

    DIR="$TMP/control/bridge_commands"

    echo "2/6 installer source guard"
    python3 - "$DIR/install_command_bus.py" <<'PY'
from pathlib import Path
import py_compile, sys
p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")
# Hotfix the 2026-09-29 provisional installer typo only in the temporary copy.
repls = {
    '"live_trading": false,': '"live_trading": False,',
    '"paid_actions": false,': '"paid_actions": False,',
    '"wallet_actions": false,': '"wallet_actions": False,',
    '"wsl_remote_writes": false': '"wsl_remote_writes": False',
}
changed = False
for old, new in repls.items():
    if old in s:
        s = s.replace(old, new)
        changed = True
p.write_text(s, encoding="utf-8")
py_compile.compile(str(p), doraise=True)
if any(x in s for x in repls):
    raise SystemExit("FOUT: lowercase boolean installer typo remains")
print("PASS: installer temporary source guarded" + (" (hotfixed)" if changed else ""))
PY
    RC=$?
    if [ "$RC" -ne 0 ]; then
        echo "FOUT: installer source guard rc=$RC"
        return "$RC"
    fi

    echo "3/6 deterministic selftest"
    python3 "$DIR/selftest.py"
    RC=$?
    if [ "$RC" -ne 0 ]; then
        echo "FOUT: selftest rc=$RC"
        return "$RC"
    fi

    echo "4/6 install"
    python3 "$DIR/install_command_bus.py" --route-task "$ROUTE_TASK"
    RC=$?
    if [ "$RC" -ne 0 ]; then
        echo "FOUT: installer rc=$RC (installer rollback hoort reeds uitgevoerd te zijn)"
        return "$RC"
    fi

    echo "5/6 systemd status"
    systemctl --user is-active prediction-command-bus.timer || true
    systemctl --user is-active prediction-chat-wake.service || true
    systemctl --user is-active prediction-chat-router.service || true
    systemctl --user is-active prediction-chat-command.service || true

    echo "6/6 qualification"
    if [ -f "$HOME/.local/state/prediction-command-bus/qualification.json" ]; then
        cat "$HOME/.local/state/prediction-command-bus/qualification.json"
    else
        echo "FOUT: qualification.json ontbreekt"
        return 1
    fi

    echo "SAFE BOOTSTRAP KLAAR"
    return 0
}

main "$@"
RC=$?
echo "BOOTSTRAP_RC=$RC"
return "$RC" 2>/dev/null || true
