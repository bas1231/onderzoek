from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ai_response
import candidate_queue


RUN_ID = "hourly-20261004T220000+0200"


def _configure(monkeypatch, root: Path):
    runs = root / "knowledge/runs"
    packets = runs / "agent_packets"
    candidates = root / "knowledge/candidates"
    monkeypatch.setattr(ai_response, "ROOT", root)
    monkeypatch.setattr(ai_response, "RUNS", runs)
    monkeypatch.setattr(ai_response, "PACKETS", packets)
    monkeypatch.setattr(ai_response, "CANDIDATES", candidates)
    monkeypatch.setattr(ai_response, "_record_graphs", lambda run_id, response: {"ok": True})
    packet_dir = packets / RUN_ID
    packet_dir.mkdir(parents=True, exist_ok=True)
    (packet_dir / "discovery.json").write_text(json.dumps({
        "run_id": RUN_ID,
        "agent_id": "discovery",
        "status": "READY",
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "openai_api": False,
    }) + "\n")
    return candidates


def _proposal(lane="primary_scout", refs=None):
    return {
        "candidate_key": "primary-maker-anomaly-v1",
        "lane": lane,
        "hypothesis": "A recurring public market anomaly may predict temporary mispricing.",
        "mechanism": "Public order-flow or attention imbalance may create a transient pricing error; unproven.",
        "open_question": "Does the signal predict out of sample after fees and execution constraints?",
        "next_decisive_test": "Freeze a point-in-time sample and test net executable economics out of sample.",
        "evidence_summary": "Two public observations suggest the same anomaly, but no edge is established.",
        "evidence_refs": refs if refs is not None else ["evidence/source-a", "evidence/source-b"],
    }


def _response(proposal):
    return {
        "schema": "PVA_AI_RESPONSE_V1",
        "run_id": RUN_ID,
        "economic_conclusion": "NO_PROVEN_EDGE",
        "role_results": [{
            "agent_id": "discovery",
            "status": "COMPLETED",
            "finding": "Primary scout found a candidate-worthy anomaly for Director review.",
            "evidence_refs": ["evidence/source-a", "evidence/source-b"],
            "candidate_ids": [],
            "candidate_proposals": [proposal],
            "capability_results": {},
            "validation_results": [],
            "failure_pattern_ids": [],
            "next_decisive_question": "Can the anomaly survive a frozen prospective test?",
            "local_task_required": False,
            "local_task_spec": None,
        }],
        "candidate_decisions": [],
        "director_decision": "Create an unproven research candidate only.",
        "local_tasks": [],
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "openai_api": False,
    }


def test_primary_scout_proposal_creates_one_unproven_candidate_and_is_idempotent(tmp_path, monkeypatch):
    candidates = _configure(monkeypatch, tmp_path)
    response = _response(_proposal())

    first = ai_response.apply_response(response, RUN_ID, write=True)
    assert len(first["candidate_creations"]) == 1
    files = list(candidates.glob("*.json"))
    assert len(files) == 1
    candidate = json.loads(files[0].read_text())
    assert candidate["provenance"] == "AUTONOMOUS_PRIMARY_SCOUT"
    assert candidate["queue_status"] == "NEEDS_DIRECTOR"
    assert candidate["decision"] == "UNPROVEN"
    assert candidate["scientific_status"] == "NO_PROVEN_EDGE"
    assert candidate["scout_evidence_refs"] == ["evidence/source-a", "evidence/source-b"]
    assert candidate["evidence_refs"] == []
    assert candidate["live_trading"] is False
    assert candidate["paid_actions"] is False
    assert candidate["wallet_actions"] is False

    second = ai_response.apply_response(response, RUN_ID, write=True)
    assert second["candidate_creations"] == []
    assert len(list(candidates.glob("*.json"))) == 1

    monkeypatch.setattr(candidate_queue, "ROOT", tmp_path)
    monkeypatch.setattr(candidate_queue, "CANDIDATES", candidates)
    monkeypatch.setattr(candidate_queue, "RUNS", tmp_path / "knowledge/runs")
    queue = candidate_queue.build_queue(write_candidates=False)
    row = next(x for x in queue["queue"] if x["candidate_id"] == candidate["candidate_id"])
    assert row["queue_status"] == "NEEDS_DIRECTOR"
    assert row["priority"] == "P2"


def test_recon_scout_proposal_cannot_bypass_hunt_gate(tmp_path, monkeypatch):
    _configure(monkeypatch, tmp_path)
    response = _response(_proposal(lane="recon_scout"))
    try:
        ai_response.apply_response(response, RUN_ID, write=True)
    except ai_response.ValidationError as exc:
        assert "only primary_scout proposals" in str(exc)
    else:
        raise AssertionError("recon_scout proposal bypassed deterministic HUNT gate")


def test_primary_scout_proposal_cannot_cite_unreturned_evidence(tmp_path, monkeypatch):
    _configure(monkeypatch, tmp_path)
    response = _response(_proposal(refs=["evidence/not-returned"]))
    try:
        ai_response.apply_response(response, RUN_ID, write=True)
    except ai_response.ValidationError as exc:
        assert "must be role evidence" in str(exc)
    else:
        raise AssertionError("proposal accepted evidence outside discovery role result")
