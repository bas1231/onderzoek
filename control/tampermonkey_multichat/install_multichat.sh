#!/usr/bin/env bash

# Interactive-terminal safe: every failure is handled locally and returns from main.
# Run this script with `bash install_multichat.sh`.

main() {
    SRC_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
    DATA_DIR="$HOME/.local/share/prediction-chat-bridge"
    CONFIG_DIR="$HOME/.config/prediction-chat-bridge"
    UNIT_DIR="$HOME/.config/systemd/user"
    SOURCE_DIR="$HOME/prediction_chat_wake_bridge"
    TOKEN_FILE="$CONFIG_DIR/token"
    WAKE_UNIT="$UNIT_DIR/prediction-chat-wake.service"
    ROUTER_UNIT="$UNIT_DIR/prediction-chat-router.service"
    STAMP="$(date +%Y%m%d_%H%M%S)"
    BACKUP_DIR="$DATA_DIR/backups/multichat_$STAMP"

    echo "=== PREDICTION TAMPERMONKEY MULTICHAT INSTALLER ==="
    echo "Bron: $SRC_DIR"
    echo "Backup: $BACKUP_DIR"

    if [ -z "$SRC_DIR" ] || [ ! -f "$SRC_DIR/bridge_server_v2.py" ] || [ ! -f "$SRC_DIR/command_router.py" ] || [ ! -f "$SRC_DIR/prediction-chat-wake.user.js" ]; then
        echo "FOUT: bronbestanden ontbreken. Niets gewijzigd."
        return 1
    fi

    if ! mkdir -p "$DATA_DIR/outbox" "$DATA_DIR/sent" "$DATA_DIR/routes" "$CONFIG_DIR" "$UNIT_DIR" "$SOURCE_DIR" "$BACKUP_DIR"; then
        echo "FOUT: mappen konden niet worden aangemaakt."
        return 1
    fi

    [ -f "$DATA_DIR/bridge_server.py" ] && cp -p "$DATA_DIR/bridge_server.py" "$BACKUP_DIR/bridge_server.py" || true
    [ -f "$DATA_DIR/command_router.py" ] && cp -p "$DATA_DIR/command_router.py" "$BACKUP_DIR/command_router.py" || true
    [ -f "$SOURCE_DIR/prediction-chat-wake.user.js" ] && cp -p "$SOURCE_DIR/prediction-chat-wake.user.js" "$BACKUP_DIR/prediction-chat-wake.user.js" || true
    [ -f "$WAKE_UNIT" ] && cp -p "$WAKE_UNIT" "$BACKUP_DIR/prediction-chat-wake.service" || true
    [ -f "$ROUTER_UNIT" ] && cp -p "$ROUTER_UNIT" "$BACKUP_DIR/prediction-chat-router.service" || true

    rollback() {
        echo "=== ROLLBACK ==="
        if [ -f "$BACKUP_DIR/bridge_server.py" ]; then
            cp -p "$BACKUP_DIR/bridge_server.py" "$DATA_DIR/bridge_server.py" || true
        fi
        if [ -f "$BACKUP_DIR/prediction-chat-wake.user.js" ]; then
            cp -p "$BACKUP_DIR/prediction-chat-wake.user.js" "$SOURCE_DIR/prediction-chat-wake.user.js" || true
        fi
        if [ -f "$BACKUP_DIR/prediction-chat-wake.service" ]; then
            cp -p "$BACKUP_DIR/prediction-chat-wake.service" "$WAKE_UNIT" || true
        fi
        if [ -f "$BACKUP_DIR/prediction-chat-router.service" ]; then
            cp -p "$BACKUP_DIR/prediction-chat-router.service" "$ROUTER_UNIT" || true
        else
            systemctl --user disable --now prediction-chat-router.service >/dev/null 2>&1 || true
        fi
        systemctl --user daemon-reload >/dev/null 2>&1 || true
        systemctl --user restart prediction-chat-wake.service >/dev/null 2>&1 || true
        echo "Rollback uitgevoerd. Terminal blijft open."
    }

    if [ ! -s "$TOKEN_FILE" ]; then
        if ! python3 - <<'PY' > "$TOKEN_FILE"
import secrets
print(secrets.token_urlsafe(32))
PY
        then
            echo "FOUT: token kon niet worden gemaakt."
            rollback
            return 1
        fi
        chmod 0600 "$TOKEN_FILE" || true
    fi

    if ! install -m 0755 "$SRC_DIR/bridge_server_v2.py" "$DATA_DIR/bridge_server.py"; then
        echo "FOUT: bridge_server.py installeren mislukt."
        rollback
        return 1
    fi
    if ! install -m 0755 "$SRC_DIR/command_router.py" "$DATA_DIR/command_router.py"; then
        echo "FOUT: command_router.py installeren mislukt."
        rollback
        return 1
    fi
    if ! install -m 0644 "$SRC_DIR/prediction-chat-wake.user.js" "$DATA_DIR/prediction-chat-wake.user.js"; then
        echo "FOUT: userscript naar datamap installeren mislukt."
        rollback
        return 1
    fi
    if ! install -m 0644 "$SRC_DIR/prediction-chat-wake.user.js" "$SOURCE_DIR/prediction-chat-wake.user.js"; then
        echo "FOUT: userscript bronkopie installeren mislukt."
        rollback
        return 1
    fi

    cat > "$WAKE_UNIT" <<'UNIT'
[Unit]
Description=Prediction Chat Wake Bridge (Tampermonkey multi-chat)
After=default.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 %h/.local/share/prediction-chat-bridge/bridge_server.py --host 127.0.0.1 --port 8765
Restart=always
RestartSec=2
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=default.target
UNIT

    cat > "$ROUTER_UNIT" <<'UNIT'
[Unit]
Description=Prediction Chat Multi-Chat Command Router
After=default.target prediction-chat-command.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 %h/.local/share/prediction-chat-bridge/command_router.py --host 127.0.0.1 --port 8767
Restart=always
RestartSec=2
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=default.target
UNIT

    if ! systemctl --user daemon-reload; then
        echo "FOUT: systemd daemon-reload mislukt."
        rollback
        return 1
    fi

    if ! systemctl --user is-active --quiet prediction-chat-command.service; then
        echo "FOUT: bestaande prediction-chat-command.service op 8766 draait niet."
        echo "De receiver wordt niet automatisch gewijzigd of vervangen."
        rollback
        return 1
    fi

    if ! systemctl --user restart prediction-chat-wake.service; then
        echo "FOUT: wake-service restart mislukt."
        rollback
        return 1
    fi
    if ! systemctl --user enable --now prediction-chat-router.service; then
        echo "FOUT: router-service starten mislukt."
        rollback
        return 1
    fi

    TOKEN="$(cat "$TOKEN_FILE" 2>/dev/null)"
    if [ -z "$TOKEN" ]; then
        echo "FOUT: token is leeg na installatie."
        rollback
        return 1
    fi

    WAKE_HEALTH="$(curl -fsS -H "Authorization: Bearer $TOKEN" http://localhost:8765/health 2>/dev/null)"
    ROUTER_HEALTH="$(curl -fsS -H "Authorization: Bearer $TOKEN" http://localhost:8767/health 2>/dev/null)"

    if ! printf '%s' "$WAKE_HEALTH" | grep -q '"multichat":true'; then
        echo "FOUT: wake health-check is niet multi-chat groen: $WAKE_HEALTH"
        rollback
        return 1
    fi
    if ! printf '%s' "$ROUTER_HEALTH" | grep -q '"ok":true'; then
        echo "FOUT: router health-check mislukt: $ROUTER_HEALTH"
        rollback
        return 1
    fi

    echo
    echo "=== INSTALLATIE GROEN ==="
    echo "Wake:   $WAKE_HEALTH"
    echo "Router: $ROUTER_HEALTH"
    echo "8766 command receiver: ACTIEF en NIET GEWIJZIGD"
    echo
    echo "Tampermonkey-update URL:"
    echo "http://localhost:8765/prediction-chat-wake.user.js"
    echo
    echo "Open die URL in Chrome en bevestig de Tampermonkey update/installatie."
    echo "Daarna werken verschillende ChatGPT-chats met eigen chat_id tegelijk."
    echo "De bestaande gekoppelde chat kan via Tampermonkey-menu 'Deze chat als fallback instellen' autonome wakeups blijven ontvangen."
    echo
    echo "Backup bewaard in: $BACKUP_DIR"
    echo "KLAAR — terminal blijft open."
    return 0
}

main "$@"
