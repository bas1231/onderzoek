from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def content():
    return (
        ROOT
        / "control/browser_extension/content.js"
    ).read_text(encoding="utf-8")

def test_e411_marker_fallback_exists():
    src = content()
    assert "E411 marker fallback:" in src
    assert "extractTaskBlocks(bodyText)" in src
    assert "fallbackBlocks" in src

def test_user_quoted_tasks_are_excluded():
    src = content()
    assert """'[data-message-author-role="user"]'""" in src
    assert "userTexts.some(" in src
    assert "text => text.includes(block)" in src

def test_raw_body_is_not_returned_as_assistant():
    src = content()
    assert (
        "return document.body ? [document.body] : [];"
        not in src
    )

def test_normal_assistant_selector_remains_primary():
    src = content()
    assert """'[data-message-author-role="assistant"]'""" in src
    assert "specific.push({" in src

def test_content_version_bumped():
    src = content()
    assert 'const CONTENT_VERSION = "0.8.0";' in src
