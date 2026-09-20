from pathlib import Path


SOURCE = Path(
    "control/browser_extension/content.js"
).read_text(encoding="utf-8")


def test_ai_markers_exist():
    assert "PREDICTION_AI_WORK_BUNDLE" in SOURCE
    assert "END_PREDICTION_AI_WORK_BUNDLE" in SOURCE


def test_dedicated_ai_routes():
    assert '"/ai-outbox"' in SOURCE
    assert '"/ai-ack"' in SOURCE


def test_ai_kind_checked():
    assert 'item.kind !== "AI_WORK_BUNDLE"' in SOURCE


def test_executor_route_must_be_false():
    assert (
        "guardrails.direct_executor_route !== false"
        in SOURCE
    )


def test_cost_and_live_guardrails_checked():
    assert "guardrails.live_trading !== false" in SOURCE
    assert "guardrails.paid_actions !== false" in SOURCE
    assert "guardrails.wallet_actions !== false" in SOURCE
    assert "guardrails.openai_api !== false" in SOURCE


def test_ack_happens_after_send():
    send_pos = SOURCE.index(
        "const sent = await insertAndSend("
    )

    # Use AI ack occurrence, not ordinary ack.
    ack_pos = SOURCE.index(
        '"/ai-ack"',
        send_pos,
    )

    assert ack_pos > send_pos


def test_ai_and_normal_outbox_both_exist():
    assert "pollAiOutbox();" in SOURCE
    assert "pollOutbox();" in SOURCE
