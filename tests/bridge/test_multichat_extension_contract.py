from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_background_emits_chat_and_consumer_routing_headers():
    source = (ROOT / "control/browser_extension/background.js").read_text(
        encoding="utf-8"
    )

    assert '"predictionTaskClientMapV1"' in source
    assert 'headers["X-Prediction-Client-Id"]' in source
    assert 'headers["X-Prediction-Consumer-Id"]' in source
    assert "taskClientForRequest" in source
    assert "consumerIdFromSender" in source


def test_project_auto_arm_still_allows_multiple_chats_in_same_project():
    background = (ROOT / "control/browser_extension/background.js").read_text(
        encoding="utf-8"
    )
    content = (ROOT / "control/browser_extension/content.js").read_text(
        encoding="utf-8"
    )
    capture = (ROOT / "control/browser_extension/ai_response_capture.js").read_text(
        encoding="utf-8"
    )

    assert "stored.armedProjectKey" in background
    assert "stored.armedProjectKey" in content
    assert "stored.armedProjectKey" in capture
    assert "projectKeyFromUrl" in background
    assert "projectKeyFromCurrentUrl" in content
    assert "projectKeyFromCurrentUrl" in capture
