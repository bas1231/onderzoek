#!/usr/bin/env bash
# Install the read-only public METAR race collector as user services.
# No trading, wallet or paid API capability is installed.

main() {
    SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)" || return 1
    ROOT="$(cd -- "$SCRIPT_DIR/../.." 2>/dev/null && pwd)" || return 1
    UNIT_DIR="$HOME/.config/systemd/user"
    PY="$ROOT/.venv/bin/python"
    [ -x "$PY" ] || PY="$(command -v python3 2>/dev/null)"

    if [ -z "$ROOT" ] || [ ! -f "$ROOT/control/weather/public_metar_race.py" ]; then
        echo "FOUT: repository/weather bron niet gevonden; niets gewijzigd."
        return 1
    fi
    if [ -z "$PY" ] || [ ! -x "$PY" ]; then
        echo "FOUT: Python niet gevonden; niets gewijzigd."
        return 1
    fi

    echo "=== Weather public METAR race preflight ==="
    echo "Repo:   $ROOT"
    echo "Python: $PY"

    if ! "$PY" "$ROOT/control/jobs/validate_public_metar_race.py" --offline; then
        echo "FOUT: offline technical/adversarial validation faalde; niets geïnstalleerd."
        return 1
    fi

    echo
    echo "=== Prospectieve publieke smoke-test ==="
    if ! "$PY" "$ROOT/control/jobs/validate_public_metar_race.py"; then
        echo "FOUT: publieke smoke-test faalde; niets als service geactiveerd."
        return 1
    fi

    mkdir -p "$UNIT_DIR" || return 1

    cat > "$UNIT_DIR/prediction-weather-public-metar-race.service" <<UNIT
[Unit]
Description=Prediction Research public METAR source-race recorder
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$ROOT
ExecStart=$PY $ROOT/control/weather/public_metar_race.py --interval-sec 5 --max-stations 12
Restart=always
RestartSec=3
Nice=5
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=default.target
UNIT

    cat > "$UNIT_DIR/prediction-weather-public-metar-analysis.service" <<UNIT
[Unit]
Description=Prediction Research public METAR source-race analysis
After=prediction-weather-public-metar-race.service

[Service]
Type=oneshot
WorkingDirectory=$ROOT
ExecStart=$PY $ROOT/control/weather/analyze_public_metar_race.py
Nice=10
NoNewPrivileges=true
PrivateTmp=true
UNIT

    cat > "$UNIT_DIR/prediction-weather-public-metar-analysis.timer" <<'UNIT'
[Unit]
Description=Analyze public METAR source-race evidence every 30 minutes

[Timer]
OnBootSec=10min
OnUnitActiveSec=30min
Persistent=true
Unit=prediction-weather-public-metar-analysis.service

[Install]
WantedBy=timers.target
UNIT

    if ! systemctl --user daemon-reload; then
        echo "FOUT: systemd daemon-reload faalde."
        return 1
    fi
    if ! systemctl --user enable --now prediction-weather-public-metar-race.service; then
        echo "FOUT: collector-service kon niet worden gestart."
        return 1
    fi
    if ! systemctl --user enable --now prediction-weather-public-metar-analysis.timer; then
        echo "FOUT: analyzer-timer kon niet worden gestart."
        return 1
    fi

    sleep 2
    echo
    echo "=== STATUS ==="
    systemctl --user --no-pager --full status prediction-weather-public-metar-race.service 2>/dev/null | sed -n '1,12p'
    systemctl --user --no-pager list-timers prediction-weather-public-metar-analysis.timer 2>/dev/null || true
    echo
    echo "KLAAR: alleen read-only publieke bronmeting geactiveerd; economische status blijft NO_PROVEN_EDGE."
    return 0
}

main "$@"
