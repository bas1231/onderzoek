from pathlib import Path


def test_installer_keeps_fast_deadman_runtime_guards():
    path = Path(__file__).with_name("install_hardened_bridge.py")
    text = path.read_text(encoding="utf-8")

    required = [
        "FAST_DEADMAN_SECONDS = 15.0",
        "DEFAULT_HEARTBEAT_INTERVAL = 15.0",
        "heartbeat_message(token)",
        "heartbeat_retry_nonce",
        "heartbeat_fresh_task_id_required",
        "HEARTBEAT_FAST_DEADMAN=1",
        "HEARTBEAT_RETRY_NONCE=1",
        "HEARTBEAT_FRESH_TASK_ID_REQUIRED=1",
    ]

    missing = [item for item in required if item not in text]
    assert not missing, f"missing durable fast-deadman guards: {missing}"
