from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / "control" / "browser_extension" / "patch_result_ack_presend_gate.py"

spec = spec_from_file_location("result_ack_patch", PATCH)
module = module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def test_patch_inserts_presend_gate_once():
    source = "prefix\n" + module.OLD + "\nsuffix\n"
    patched, changed = module.patch_text(source)
    assert changed is True
    assert module.MARKER in patched
    assert "await resultAckPending(item.task_id)" in patched
    assert patched.index("await resultAckPending(item.task_id)") < patched.index("const sent = await insertAndSend(")


def test_patch_is_idempotent():
    source = "prefix\n" + module.OLD + "\nsuffix\n"
    once, changed = module.patch_text(source)
    assert changed is True
    twice, changed_again = module.patch_text(once)
    assert changed_again is False
    assert twice == once
    assert twice.count(module.MARKER) == 1


def test_patch_fails_closed_on_unknown_source():
    try:
        module.patch_text("unexpected source")
    except ValueError as exc:
        assert "audited pollOutbox anchor not found" in str(exc)
    else:
        raise AssertionError("unknown source must fail closed")
