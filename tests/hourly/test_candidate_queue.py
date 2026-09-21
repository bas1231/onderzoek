import importlib.util
import json
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


def test_proof_review_never_mutates_candidate_or_declares_final_edge(tmp_path):
    mod=load_module()
    mod.ROOT=tmp_path
    mod.RUNS=tmp_path/"knowledge/runs"
    mod.RUNS.mkdir(parents=True)
    before=list((tmp_path/"knowledge").rglob("*.json"))
    path=mod.write_proof_review("run-x",{"proof_candidates":["X"],"proof_rejections":{"Y":["missing_economics"]}})
    data=json.loads(path.read_text())
    assert data["status"]=="DIRECTOR_REVIEW_REQUIRED"
    assert data["proof_candidates"]==["X"]
    assert data["automatic_candidate_mutation"] is False
    assert data["automatic_proven_edge"] is False
    assert not (tmp_path/"knowledge/candidates/X.json").exists()
    assert path not in before

def test_no_proof_candidate_review_is_null_result(tmp_path):
    mod=load_module()
    mod.ROOT=tmp_path
    mod.RUNS=tmp_path/"knowledge/runs"
    mod.RUNS.mkdir(parents=True)
    path=mod.write_proof_review("run-null",{"proof_candidates":[]})
    data=json.loads(path.read_text())
    assert data["status"]=="NO_PROVEN_EDGE"
