import importlib.util
import sys
from pathlib import Path


ROOT = Path.cwd()


def load_module():
    path = ROOT / "control/hourly/candidate_queue.py"
    spec = importlib.util.spec_from_file_location(
        "candidate_queue",
        path,
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_discovered_needs_director():
    mod = load_module()
    c = {"candidate_id": "X", "phase": "DISCOVERED"}
    assert mod.infer_queue_status(c) == "NEEDS_DIRECTOR"
    assert mod.infer_priority(c) == "P2"


def test_monitoring_is_running_p1():
    mod = load_module()
    c = {
        "candidate_id": "X",
        "phase": "MECHANISM_DEFINED",
        "prospective_monitoring": {"enabled": True},
    }
    assert mod.infer_queue_status(c) == "RUNNING"
    assert mod.infer_priority(c) == "P1"


def test_protocol_waiting_is_p1():
    mod = load_module()
    c = {
        "candidate_id": "X",
        "phase": "MECHANISM_DEFINED",
        "prospective_protocols": ["protocol.json"],
    }
    assert mod.infer_queue_status(c) == "WAITING_FOR_RESULT"
    assert mod.infer_priority(c) == "P1"


def test_aging_does_not_change_evidence_status():
    mod = load_module()
    c = {
        "candidate_id": "X",
        "phase": "DISCOVERED",
        "queue_status": "QUEUED",
        "priority": "P3",
        "queue_entered_at": "2020-01-01T00:00:00+00:00",
    }

    rank, _, _ = mod.effective_priority(c)

    assert rank <= 2
    assert c["queue_status"] == "QUEUED"
    assert c["priority"] == "P3"


def test_guardrails_forced_false():
    mod = load_module()
    c = {
        "candidate_id": "X",
        "phase": "DISCOVERED",
        "live_trading": True,
        "paid_actions": True,
        "wallet_actions": True,
    }

    c, changed = mod.normalize_candidate(c)

    assert changed
    assert c["live_trading"] is False
    assert c["paid_actions"] is False
    assert c["wallet_actions"] is False
