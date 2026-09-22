import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXT = ROOT / "control/browser_extension"


def read(name: str) -> str:
    return (
        EXT / name
    ).read_text(
        encoding="utf-8"
    )


def test_manifest_no_longer_auto_injects():
    manifest = json.loads(
        read("manifest.json")
    )

    manifest_version = tuple(
        int(part)
        for part in manifest["version"].split(".")
    )

    assert manifest_version >= (0, 9, 0)

    assert (
        "content_scripts"
        not in manifest
    )

    assert (
        manifest["background"]
        ["service_worker"]
        == "background.js"
    )


def test_background_only_targets_armed_tabs():
    src = read(
        "background.js"
    )

    assert (
        'const RUNTIME_VERSION = "0.9.0";'
        in src
    )

    assert (
        "tabMatchesArmedState"
        in src
    )

    assert (
        'reason: "tab not armed"'
        in src
    )

    assert (
        '"armedProjectKey"'
        in src
    )


def test_content_context_guard():
    src = read(
        "content.js"
    )

    assert (
        "const CONTENT_VERSION ="
        in src
    )

    assert (
        'const CONTENT_VERSION = "0.9.1";'
        in src
    )

    assert (
        "extensionContextAlive"
        in src
    )

    assert (
        "contextInvalidated"
        in src
    )

    assert (
        "predictionBridgePing"
        in src
    )


def test_capture_context_guard():
    src = read(
        "ai_response_capture.js"
    )

    assert (
        'const CAPTURE_VERSION = "0.9.0";'
        in src
    )

    assert (
        "extensionContextAlive"
        in src
    )

    assert (
        "contextInvalidated"
        in src
    )

    assert (
        "predictionAiCapturePing"
        in src
    )
