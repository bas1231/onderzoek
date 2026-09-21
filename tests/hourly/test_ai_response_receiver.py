import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path.cwd()


def load_from(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_receiver():
    return load_from(
        ROOT / "control/hourly/ai_response_receiver.py",
        "ai_response_receiver_test",
    )


def configure_tmp_receiver(mod, tmp_path, monkeypatch):
    runs = tmp_path / "knowledge/runs"
    packets = runs / "agent_packets"
    candidates = tmp_path / "knowledge/candidates"
    runs.mkdir(parents=True)
    packets.mkdir(parents=True)
    candidates.mkdir(parents=True)

    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(mod, "RUNS", runs)
    monkeypatch.setattr(mod, "PACKETS", packets)

    real_loader = mod.load_module

    def patched_loader(name, path):
        actual = ROOT / "control/hourly" / path.name
        loaded = load_from(actual, name + "_tmp")
        if path.name == "ai_response.py":
            loaded.ROOT = tmp_path
            loaded.RUNS = runs
            loaded.PACKETS = packets
            loaded.CANDIDATES = candidates
        elif path.name == "agent_orchestrator.py":
            loaded.ROOT = tmp_path
            loaded.PACKETS = packets
        else:
            return real_loader(name, path)
        return loaded

    monkeypatch.setattr(mod, "load_module", patched_loader)
    return runs, packets


def write_bundle_and_packets(runs, packets, run_id):
    run_dir = packets / run_id
    run_dir.mkdir(parents=True)

    for role in ("algebra", "research_director"):
        (run_dir / f"{role}.json").write_text(json.dumps({
            "agent_id": role,
            "run_id": run_id,
            "status": "READY",
            "priority": "P3" if role == "algebra" else "P1",
            "input_refs": ["evidence.json"] if role == "algebra" else [],
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
        }))

    (runs / f"{run_id}-ai-work-bundle.json").write_text(json.dumps({
        "schema": "PVA_AI_WORK_BUNDLE_V1",
        "run_id": run_id,
        "ready_roles": [
            {"agent_id": "algebra"},
            {"agent_id": "research_director"},
        ],
    }))


def response(run_id, include_director=True):
    roles = [{
        "agent_id": "algebra",
        "status": "COMPLETED",
        "finding": "WATCH triage completed; no proven edge.",
        "evidence_refs": ["evidence.json"],
        "candidate_ids": ["CAND-X"],
        "next_decisive_question": None,
        "local_task_required": False,
        "local_task_spec": None,
    }]
    if include_director:
        roles.append({
            "agent_id": "research_director",
            "status": "COMPLETED",
            "finding": "Cycle closed with NO_PROVEN_EDGE.",
            "evidence_refs": [],
            "candidate_ids": [],
            "next_decisive_question": None,
            "local_task_required": False,
            "local_task_spec": None,
        })
    return {
        "run_id": run_id,
        "role_results": roles,
        "candidate_decisions": [],
        "director_decision": "Keep WATCH at triage only.",
        "economic_conclusion": "NO_PROVEN_EDGE",
        "local_tasks": [],
    }


def test_missing_ready_role_is_rejected(tmp_path, monkeypatch):
    mod = load_receiver()
    runs, packets = configure_tmp_receiver(mod, tmp_path, monkeypatch)
    run_id = "hourly-20260921T190000+0200"
    write_bundle_and_packets(runs, packets, run_id)

    with pytest.raises(mod.ResponseReceiverError, match="missing ready roles"):
        mod.receive({
            "run_id": run_id,
            "response": response(run_id, include_director=False),
        })

    assert not (runs / f"{run_id}-ai-response.json").exists()
    assert not (runs / f"{run_id}-ai-response-receipt.json").exists()


def test_complete_response_applies_and_is_idempotent(tmp_path, monkeypatch):
    mod = load_receiver()
    runs, packets = configure_tmp_receiver(mod, tmp_path, monkeypatch)
    run_id = "hourly-20260921T190000+0200"
    write_bundle_and_packets(runs, packets, run_id)
    payload = {
        "run_id": run_id,
        "response": response(run_id),
    }

    out = mod.receive(payload)
    assert out["ok"] is True
    assert out["already_applied"] is False
    assert out["economic_conclusion"] == "NO_PROVEN_EDGE"
    assert out["live_trading"] is False
    assert out["paid_actions"] is False
    assert out["wallet_actions"] is False

    algebra = json.loads(
        (packets / run_id / "algebra.json").read_text()
    )
    assert algebra["status"] == "COMPLETED"
    assert algebra["ai_result"]["candidate_ids"] == ["CAND-X"]
    assert algebra["live_trading"] is False
    assert algebra["paid_actions"] is False
    assert algebra["wallet_actions"] is False

    second = mod.receive(payload)
    assert second["ok"] is True
    assert second["already_applied"] is True


def test_conflicting_second_response_is_rejected(tmp_path, monkeypatch):
    mod = load_receiver()
    runs, packets = configure_tmp_receiver(mod, tmp_path, monkeypatch)
    run_id = "hourly-20260921T190000+0200"
    write_bundle_and_packets(runs, packets, run_id)
    first = response(run_id)
    mod.receive({"run_id": run_id, "response": first})

    conflicting = response(run_id)
    conflicting["role_results"][0]["finding"] = "different"

    with pytest.raises(mod.ResponseReceiverError, match="conflicting"):
        mod.receive({
            "run_id": run_id,
            "response": conflicting,
        })
