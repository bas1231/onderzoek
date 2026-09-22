from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_popup_roundtrip_ack_is_mandatory():
    src = (
        ROOT
        / "control"
        / "browser_extension"
        / "popup.js"
    ).read_text(encoding="utf-8")

    result_pos = src.index("result.data.result")
    ack_pos = src.index('"/ack"', result_pos)
    pass_pos = src.index(
        "ROUND TRIP PASS",
        ack_pos,
    )

    assert result_pos < ack_pos < pass_pos
    assert "ACK FAILED" in src
    assert "ACK PASS" in src
    assert "attempt < 5" in src
    assert "90000" in src
    assert "within 90 seconds." in src


def test_incident_ack_is_persistently_resolved():
    src = (
        ROOT
        / "control"
        / "browser_bridge.py"
    ).read_text(encoding="utf-8")

    assert "_resolve_incident_after_ack" in src
    assert 'data["status"] = "RESOLVED"' in src
    assert "BROWSER_ACK_RESOLVED" in src
