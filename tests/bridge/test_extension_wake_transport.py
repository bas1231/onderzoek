from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_extension_uses_canonical_wake_next_ack_without_tampermonkey_dependency():
    source = (
        ROOT
        / "control"
        / "browser_extension"
        / "content.js"
    ).read_text(encoding="utf-8")

    assert 'const CONTENT_VERSION = "0.10.0"' in source
    assert "async function pollWakeQueue()" in source
    assert '"/next?chat_id="' in source
    assert '"/ack"' in source
    assert "event_id:" in source
    assert "chat_id:" in source
    assert "consumer_id:" in source
    assert "insertAndConfirmUserTurn" in source
    assert "matchingUserTurnCount" in source
    assert "recentUserTurnHasWakeMessage" in source
    assert "markWakeEventSeen" in source
    assert "wakeTransportDetected = true" in source
    assert "26000" in source
    assert "GM_" not in source


def test_browser_ack_is_not_encoded_as_continuation_success():
    source = (
        ROOT
        / "control"
        / "browser_extension"
        / "content.js"
    ).read_text(encoding="utf-8")

    assert "NEXT_TASK_ACCEPTED" not in source
    assert "CONTINUE_SENT" not in source
    assert "expected_next_task_id" not in source


def test_manifest_version_matches_content_transport():
    import json

    manifest = json.loads(
        (
            ROOT
            / "control"
            / "browser_extension"
            / "manifest.json"
        ).read_text(encoding="utf-8")
    )
    background = (
        ROOT
        / "control"
        / "browser_extension"
        / "background.js"
    ).read_text(encoding="utf-8")

    assert manifest["version"] == "0.10.0"
    assert 'const RUNTIME_VERSION = "0.10.0"' in background
