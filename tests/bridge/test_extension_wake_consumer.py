from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "control" / "browser_extension" / "content.js"
MANIFEST = ROOT / "control" / "browser_extension" / "manifest.json"
TAMPERMONKEY = (
    ROOT
    / "control"
    / "tampermonkey_multichat"
    / "prediction-chat-wake.user.js"
)


def source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_extension_owns_canonical_wake_next_and_ack_transport():
    text = source(CONTENT)

    assert 'const CONTENT_VERSION = "1.0.0";' in text
    assert "async function pollWake()" in text
    assert '"/next?chat_id="' in text
    assert '"&consumer_id="' in text
    assert '"/ack"' in text
    assert "event_id: eventId" in text
    assert "chat_id: identity.chatId" in text
    assert "consumer_id: consumerId" in text


def test_wake_long_poll_timeout_exceeds_server_window():
    text = source(CONTENT)

    assert "timeoutMs = 10000" in text
    assert "26000" in text
    assert "async function bridgeFetch(" in text


def test_send_click_is_not_delivery_receipt():
    text = source(CONTENT)

    assert "function exactUserTurnCount(text)" in text
    assert "const before = exactUserTurnCount(text);" in text
    assert "if (exactUserTurnCount(text) > before)" in text
    assert "send click had no observed user-turn receipt" in text


def test_refresh_dedupe_is_durable_and_scoped_to_full_event_payload():
    text = source(CONTENT)

    assert '"predictionWakeReceiptsV1"' in text
    assert "async function wakeReceiptSeen(key)" in text
    assert "async function rememberWakeReceipt(key)" in text
    assert "identity.chatId" in text
    assert "eventId" in text
    assert "message" in text
    assert "while (receipts.length > 500)" in text


def test_extension_chat_identity_matches_canonical_userscript_contract():
    extension = source(CONTENT)
    userscript = source(TAMPERMONKEY)

    for fragment in (
        "2166136261",
        "16777619",
        '.padStart(8, "0")',
        '"chat-c-"',
        'match[1].length.toString(36)',
    ):
        assert fragment in extension

    # The userscript remains reference evidence only; the extension does not
    # call into Tampermonkey or depend on its runtime.
    assert "2166136261" in userscript
    assert "16777619" in userscript
    assert "chat-c-" in userscript
    assert "GM_xmlhttpRequest" not in extension
    assert "GM_getValue" not in extension


def test_legacy_outboxes_are_not_active_pollers_anymore():
    text = source(CONTENT)
    schedule = text[text.index("  setInterval("):]

    assert "pollWake();" in schedule
    assert "pollWake()" in schedule
    assert "pollAiOutbox();" not in schedule
    assert "pollOutbox();" not in schedule


def test_manifest_version_tracks_wake_agent():
    manifest = source(MANIFEST)

    assert '"version": "1.0.0"' in manifest
    assert "wake/result bridge" in manifest
