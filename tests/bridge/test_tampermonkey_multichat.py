import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
TM = ROOT / "control" / "tampermonkey_multichat"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def configure_wake(module, tmp_path):
    data = tmp_path / "data"
    module.DATA_DIR = data
    module.OUTBOX = data / "outbox"
    module.SENT = data / "sent"
    module.ROUTES = data / "routes"
    module.DEFAULT_CHAT_FILE = data / "default_chat.json"
    module.USERSCRIPT_FILE = data / "prediction-chat-wake.user.js"
    module.TOKEN_FILE = tmp_path / "token"
    module.LEASES.clear()
    module.ensure_dirs()
    return data


def write_event(module, event_id, task_id):
    payload = {"event_id": event_id, "task_id": task_id, "message": f"wake {task_id}"}
    (module.OUTBOX / f"{event_id}.json").write_text(json.dumps(payload), encoding="utf-8")
    return payload


def write_route(module, task_id, chat_id):
    (module.ROUTES / f"{task_id}.json").write_text(
        json.dumps({"task_id": task_id, "chat_id": chat_id}), encoding="utf-8"
    )


def test_routed_event_isolated_by_chat_and_tab_lease(tmp_path):
    wake = load_module(TM / "bridge_server_v2.py", "tm_wake_a")
    configure_wake(wake, tmp_path)
    write_event(wake, "evt-1", "TASK-A")
    write_route(wake, "TASK-A", "chat-owner")

    path, item = wake.oldest_event("chat-owner", "consumer-one")
    assert path is not None
    assert item["task_id"] == "TASK-A"

    assert wake.oldest_event("chat-other", "consumer-other") == (None, None)
    assert wake.oldest_event("chat-owner", "consumer-two") == (None, None)
    assert wake.oldest_event(None, None) == (None, None)


def test_unrouted_event_goes_only_to_registered_fallback(tmp_path):
    wake = load_module(TM / "bridge_server_v2.py", "tm_wake_b")
    configure_wake(wake, tmp_path)
    write_event(wake, "evt-2", "AUTO-1")
    wake.DEFAULT_CHAT_FILE.write_text(json.dumps({"chat_id": "chat-fallback"}), encoding="utf-8")

    assert wake.oldest_event("chat-other", "consumer-other") == (None, None)
    path, item = wake.oldest_event("chat-fallback", "consumer-fallback")
    assert path is not None
    assert item["task_id"] == "AUTO-1"
    assert wake.oldest_event(None, None) == (None, None)


def test_legacy_client_can_consume_unrouted_work_before_v3_fallback(tmp_path):
    wake = load_module(TM / "bridge_server_v2.py", "tm_wake_c")
    configure_wake(wake, tmp_path)
    write_event(wake, "evt-3", "LEGACY-1")

    path, item = wake.oldest_event(None, None)
    assert path is not None
    assert item["task_id"] == "LEGACY-1"


def test_router_persists_owner_and_rejects_cross_chat_rebind(tmp_path):
    router = load_module(TM / "command_router.py", "tm_router")
    router.DATA_DIR = tmp_path / "data"
    router.ROUTES = router.DATA_DIR / "routes"
    router.DEFAULT_CHAT_FILE = router.DATA_DIR / "default_chat.json"
    router.ROUTES.mkdir(parents=True)

    first = router.write_route("TASK-X", "chat-alpha")
    assert first["chat_id"] == "chat-alpha"
    assert router.write_route("TASK-X", "chat-alpha")["chat_id"] == "chat-alpha"
    with pytest.raises(ValueError, match="TASK_ROUTE_CONFLICT"):
        router.write_route("TASK-X", "chat-beta")


def test_router_default_chat_is_atomic_and_readable(tmp_path):
    router = load_module(TM / "command_router.py", "tm_router_default")
    router.DATA_DIR = tmp_path / "data"
    router.ROUTES = router.DATA_DIR / "routes"
    router.DEFAULT_CHAT_FILE = router.DATA_DIR / "default_chat.json"
    router.DATA_DIR.mkdir(parents=True)
    router.ROUTES.mkdir(parents=True)

    result = router.write_default_chat("chat-fallback")
    assert result["chat_id"] == "chat-fallback"
    stored = json.loads(router.DEFAULT_CHAT_FILE.read_text(encoding="utf-8"))
    assert stored["chat_id"] == "chat-fallback"


def test_userscript_contract_is_multichat_and_visible_marker_only():
    text = (TM / "prediction-chat-wake.user.js").read_text(encoding="utf-8")
    assert "@version      0.4.7" in text
    assert "// @match        https://chatgpt.com/*" in text
    assert "@noframes" in text
    assert "http://localhost:8765" in text
    assert "http://localhost:8767" in text
    assert "PREDICTION_CMD" in text
    assert "chat_id" in text
    assert "consumer_id" in text
    assert "data-message-author-role=\"assistant\"" in text
    assert "<<<PREDICTION_BRIDGE_TASK>>>" not in text
    assert "conversationState()" in text
    assert "preserveLegacyFallback" in text


def test_userscript_uses_official_tampermonkey_tab_api_for_identity():
    text = (TM / "prediction-chat-wake.user.js").read_text(encoding="utf-8")
    for grant in ["GM_getTab", "GM_saveTab", "GM_getTabs", "window.onurlchange"]:
        assert f"// @grant        {grant}" in text
    assert "GM_getTab(" in text
    assert "GM_saveTab(" in text
    assert "GM_getTabs(" in text
    assert "prediction_consumer_id" in text
    assert "prediction_chat_id" in text
    assert "prediction_bridge = true" in text
    assert "Toon bridge-tabs" in text
    assert "sessionStorage" not in text


def test_userscript_new_chat_is_provisional_until_real_conversation_url():
    text = (TM / "prediction-chat-wake.user.js").read_text(encoding="utf-8")
    assert "location.pathname.match(/(?:^|\\/)c\\/([^/?#]+)/)" in text
    assert "stable: false" in text
    assert "chat-pending-" in text
    assert "if (!identity.stable)" in text
    assert "wacht op vaste ChatGPT chat-ID" in text
    assert "if (!identity.stable) return false;" in text


def test_userscript_restarts_wake_loop_on_spa_url_change():
    text = (TM / "prediction-chat-wake.user.js").read_text(encoding="utf-8")
    assert "if (window.onurlchange === null)" in text
    assert "window.addEventListener('urlchange'" in text
    assert "ensureTabIdentity(true)" in text
    assert "restartWakeLoop('URL gewijzigd')" in text
    assert "wakeGeneration" in text


def test_userscript_command_dedupe_is_scoped_to_chat():
    text = (TM / "prediction-chat-wake.user.js").read_text(encoding="utf-8")
    assert "const dedupeKey = `${identity.chatId}|${marker.markerKey}`;" in text


def test_userscript_startup_is_fail_safe_before_network_runtime():
    text = (TM / "prediction-chat-wake.user.js").read_text(encoding="utf-8")
    assert "if (window.top !== window.self) return;" not in text
    assert "GM_registerMenuCommand('Toon chat-ID'" in text
    assert "status('script gestart; tabregistratie...')" in text
    assert "tab-api fallback" in text


def test_userscript_javascript_syntax_when_node_available():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    result = subprocess.run(
        [node, "--check", str(TM / "prediction-chat-wake.user.js")],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_installer_keeps_interactive_terminal_safe_and_does_not_replace_8766_receiver():
    text = (TM / "install_multichat.sh").read_text(encoding="utf-8")
    forbidden = ["set -e", "set -o errexit", "logout", "kill $$", "exec bash", "exec zsh"]
    for token in forbidden:
        assert token not in text
    assert "prediction-chat-command.service" in text
    assert "install -m 0755 \"$SRC_DIR/command_receiver.py\"" not in text
    assert "prediction-chat-router.service" in text
    assert "rollback" in text


def test_installer_waits_for_services_before_declaring_health_failure():
    text = (TM / "install_multichat.sh").read_text(encoding="utf-8")
    assert "wait_health()" in text
    assert 'while [ "$attempt" -le 20 ]' in text
    assert "sleep 0.25" in text
    assert "http://localhost:8765/health" in text
    assert "http://localhost:8767/health" in text
