#!/usr/bin/env bash

# Terminal-safe bootstrap for the Prediction command bus.
# Intentionally: no `set -e`, no `exit`, no pipe-to-bash requirement.
# All failures return from main so a sourced interactive shell remains open.

main() {
    ROUTE_TASK="${1:-BRIDGE-BUS-E001}"
    PROD="$HOME/prediction_research_prod"
    MIRROR="$HOME/.local/share/prediction-command-bus-bootstrap-safe"
    TMP="$(mktemp -d)" || { echo "FOUT: mktemp"; return 1; }

    cleanup() {
        trap - RETURN
        rm -rf "$TMP" >/dev/null 2>&1 || true
    }
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
    python3 - "$DIR/install_command_bus.py" "$DIR/patch_wake_inflight.py" <<'PY'
from pathlib import Path
import py_compile, sys

installer = Path(sys.argv[1])
patcher = Path(sys.argv[2])

# Guard known provisional installer typo in the temporary copy only.
s = installer.read_text(encoding="utf-8")
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

# The installed wake server may now be a layered wrapper:
# bridge_server.py -> bridge_server_session_bootstrap -> bridge_server_hardened
# -> bridge_server_v2.  Older installer logic only recognized a direct
# `import bridge_server_v2 as base`, misclassified the layered wrapper as the
# queue-owning base and then failed closed during the inflight patch.
layer_decl = (
    'WRAPPER_IMPORT = "import bridge_server_v2 as base"\n'
    'LAYERED_WRAPPER_IMPORTS = (\n'
    '    "import bridge_server_session_bootstrap as session",\n'
    '    "import bridge_server_hardened as hardened",\n'
    ')\n'
)
if 'LAYERED_WRAPPER_IMPORTS' not in s:
    needle = 'WRAPPER_IMPORT = "import bridge_server_v2 as base"\n'
    if needle not in s:
        raise SystemExit("FOUT: installer wrapper declaration anchor missing")
    s = s.replace(needle, layer_decl, 1)
    changed = True
old_cond = '    if WRAPPER_IMPORT in source:\n'
new_cond = '    if WRAPPER_IMPORT in source or any(marker in source for marker in LAYERED_WRAPPER_IMPORTS):\n'
if old_cond in s:
    s = s.replace(old_cond, new_cond, 1)
    changed = True
elif new_cond not in s:
    raise SystemExit("FOUT: installer wrapper condition anchor missing")
installer.write_text(s, encoding="utf-8")

p = patcher.read_text(encoding="utf-8")
if 'LAYERED_WRAPPER_IMPORTS' not in p:
    needle = 'WRAPPER_IMPORT = "import bridge_server_v2 as base"\n'
    if needle not in p:
        raise SystemExit("FOUT: patcher wrapper declaration anchor missing")
    p = p.replace(needle, layer_decl, 1)
    changed = True
if old_cond in p:
    p = p.replace(old_cond, new_cond, 1)
    changed = True
elif new_cond not in p:
    raise SystemExit("FOUT: patcher wrapper condition anchor missing")
patcher.write_text(p, encoding="utf-8")

py_compile.compile(str(installer), doraise=True)
py_compile.compile(str(patcher), doraise=True)
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
