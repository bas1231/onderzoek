from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HEARTBEAT = ROOT / "control" / "tampermonkey_multichat" / "nightshift_server_heartbeat.py"
SERVER = ROOT / "control" / "tampermonkey_multichat" / "bridge_server_hardened.py"


def test_heartbeat_activation_requires_explicit_commandmarker_opt_in():
    src = HEARTBEAT.read_text(encoding="utf-8")
    assert "--allow-commandmarker" in src
    assert "explicit_commandmarker_opt_in_required" in src
    assert '"allow_commandmarker": True' in src


def test_server_heartbeat_remains_bounded_and_not_a_scheduler_liveness_claim():
    src = SERVER.read_text(encoding="utf-8")
    assert "expires_at" in src
    assert "server_heartbeat" in src
    assert "RUNNING" not in src
