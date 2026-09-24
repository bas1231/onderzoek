#!/usr/bin/env python3
"""Fail-closed runtime attestation for the nightshift idle heartbeat."""
from __future__ import annotations

import json
from pathlib import Path
from urllib.request import Request, urlopen

HOME = Path.home()
TOKEN_FILE = HOME / ".config" / "prediction-chat-bridge" / "token"
MODE_FILE = HOME / ".local" / "share" / "prediction-chat-bridge" / "nightshift_mode.json"


def fail(reason: str) -> int:
    print(f"HEARTBEAT_IDLE10=FAIL reason={reason}")
    return 1


def main() -> int:
    if not TOKEN_FILE.is_file() or not MODE_FILE.is_file():
        return fail("state_missing")
    token = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not token:
        return fail("token_empty")

    req = Request(
        "http://127.0.0.1:8765/health",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urlopen(req, timeout=3) as resp:
            health = json.loads(resp.read(8192) or b"{}")
    except Exception:
        return fail("health_unreachable")

    try:
        mode = json.loads(MODE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return fail("mode_invalid")

    required = {
        "ok": True,
        "server_compaction": True,
        "task_dedupe": True,
        "server_heartbeat": True,
        "heartbeat_mode_enabled": True,
        "heartbeat_done_guard": True,
        "heartbeat_inactivity_reset": True,
        "heartbeat_resets_on_bridge_result": True,
        "heartbeat_resets_on_assistant_command": True,
    }
    for key, expected in required.items():
        if health.get(key) is not expected:
            return fail(f"health_{key}")

    try:
        interval = int(float(health.get("heartbeat_interval_seconds") or 0))
        mode_interval = int(float(mode.get("interval_seconds") or 0))
    except Exception:
        return fail("interval_invalid")
    if interval != 600 or mode_interval != 600:
        return fail("interval_not_600")
    if mode.get("enabled") is not True or mode.get("allow_commandmarker") is not True:
        return fail("mode_not_enabled")

    print("HEARTBEAT_IDLE10=PASS interval=600 inactivity_reset=1 done_guard=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
