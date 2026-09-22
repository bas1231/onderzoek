from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def source():
    return (
        ROOT
        / "control/browser_extension/content.js"
    ).read_text(encoding="utf-8")


def test_e412_uses_parseable_assistant_blocks():
    src = source()

    assert "selectedAssistantBlocks" in src
    assert "new Set(" in src
    assert "specific.flatMap(" in src
    assert "extractTaskBlocks(" in src
    assert "selectedAssistantBlocks.has(block)" in src


def test_e411_false_suppression_removed():
    src = source()

    assert "selectedAssistantText.includes(block)" not in src


def test_user_message_fail_closed_remains():
    src = source()

    assert """'[data-message-author-role="user"]'""" in src
    assert "text => text.includes(block)" in src


def test_content_version_is_e412():
    src = source()

    assert 'const CONTENT_VERSION = "0.8.1";' in src
