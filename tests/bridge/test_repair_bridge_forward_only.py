from pathlib import Path

REPAIR = Path(__file__).resolve().parents[2] / "control" / "browser_extension" / "repair_bridge.py"


def test_repair_is_forward_only_and_uses_ack_gate():
    text = REPAIR.read_text(encoding="utf-8")
    assert "patch_ack_presend_gate(original)" in text
    assert "ACK_GATE_MARKER not in final" in text
    assert 'data["version"] =' not in text
    assert 'const CONTENT_VERSION = "0.5.2"' not in text


def test_repair_refuses_missing_durable_invariants():
    text = REPAIR.read_text(encoding="utf-8")
    for invariant in (
        "async function flushDurableQueue()",
        "async function resultAckPending(taskId)",
        "async function flushPendingResultAcks()",
        "const CONTENT_VERSION =",
    ):
        assert invariant in text
    assert "audited bridge invariants missing" in text


def test_repair_does_not_claim_runtime_liveness():
    text = REPAIR.read_text(encoding="utf-8")
    assert "runtime_liveness=UNVERIFIED" in text
