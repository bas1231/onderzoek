from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

POPUP = (
    ROOT
    / "control/browser_extension/popup.js"
)


def source():
    return POPUP.read_text(
        encoding="utf-8"
    )


def test_real_telemetry_installed():
    src = source()

    assert (
        "BRIDGE TELEMETRY E414R1"
        in src
    )

    assert (
        "CHATGPT PAGE DIAGNOSTIC"
        not in src
    )


def test_runtime_pings_present():
    src = source()

    assert (
        "predictionBridgePing"
        in src
    )

    assert (
        "predictionAiCapturePing"
        in src
    )


def test_bridge_health_present():
    src = source()

    assert (
        "bridge_health"
        in src
    )

    assert (
        '"/health"'
        in src
    )


def test_dom_task_telemetry_present():
    src = source()

    assert (
        "body_task_ids"
        in src
    )

    assert (
        "assistant_task_ids"
        in src
    )

    assert (
        "user_task_ids"
        in src
    )

    assert (
        "canary_seen"
        in src
    )


def test_no_literal_full_task_marker():
    src = source()

    assert (
        "<<<PREDICTION_BRIDGE_TASK>>>"
        not in src
    )

    assert (
        "<<<END_PREDICTION_BRIDGE_TASK>>>"
        not in src
    )
