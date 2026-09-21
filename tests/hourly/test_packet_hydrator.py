from pathlib import Path
import importlib.util
import json
import sys


ROOT = Path.cwd()


def load_module():
    path = ROOT / "control/hourly/packet_hydrator.py"
    spec = importlib.util.spec_from_file_location(
        "packet_hydrator",
        path,
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_evidence_hydrates_packet(tmp_path):
    mod = load_module()

    routing = tmp_path / "routing.json"
    packets = tmp_path / "packets"
    packets.mkdir()

    routing.write_text(json.dumps({
        "algebra": {
            "status": "EVIDENCE_ROUTED",
            "coverage_gaps": [],
            "evidence": [{
                "source_id": "example",
                "document_sha256": "abc",
                "retrieved_at": "2026-01-01T00:00:00Z",
                "source_state": "CHANGED",
                "term": "combo",
                "snippet": "example evidence",
            }],
        }
    }))

    (packets / "algebra.json").write_text(json.dumps({
        "agent_id": "algebra",
        "status": "NO_EVIDENCE",
        "input_refs": [],
    }))

    packet = json.loads(
        (packets / "algebra.json").read_text()
    )

    routed = json.loads(routing.read_text())["algebra"]

    hydrated = mod.hydrate_packet(
        packet,
        routed,
        ROOT / "knowledge/runs/test-routing.json",
    )

    assert hydrated["status"] == "PENDING"
    assert len(hydrated["routed_evidence"]) == 1
    assert hydrated["routed_evidence"][0]["source_id"] == "example"
    assert hydrated["input_refs"] == [
        "knowledge/runs/test-routing.json"
    ]


def test_no_evidence_stays_empty():
    mod = load_module()

    packet = {
        "agent_id": "behavioral",
        "status": "NO_EVIDENCE",
        "input_refs": [],
    }

    hydrated = mod.hydrate_packet(
        packet,
        {
            "status": "NO_EVIDENCE",
            "coverage_gaps": ["missing dataset"],
            "evidence": [],
        },
        ROOT / "knowledge/runs/test-routing.json",
    )

    assert hydrated["status"] == "PENDING"
    assert hydrated["routed_evidence"] == []
    assert hydrated["coverage_gaps"] == ["missing dataset"]
    assert hydrated["input_refs"] == []


def test_recon_watch_routes_to_specialist_triage_only(tmp_path):
    m = load_module()
    m.ROOT = tmp_path
    packet_dir = tmp_path / "knowledge/runs/agent_packets/run"
    packet_dir.mkdir(parents=True)
    for role in ["settlement", "algebra", "microstructure", "behavioral", "prebuild_killer"]:
        (packet_dir / (role + ".json")).write_text(json.dumps({
            "agent_id": role,
            "status": "NO_EVIDENCE",
            "input_refs": [],
        }))

    recon_path = tmp_path / "knowledge/runs/recon/run.json"
    recon_path.parent.mkdir(parents=True)
    recon_path.write_text(json.dumps({"findings": [
        {
            "id": "RECON-WATCH",
            "candidate_key": "CAND-WATCH",
            "status": "WATCH",
            "attack_mode": "MECHANISM_BREAKER",
            "claim": "mechanism unproven",
            "sources": [{"source_id": "rules-a"}],
            "economic_model": {"public_trigger": "settlement"},
            "falsification": {
                "next_decisive_test": "test point-in-time net economics",
                "specialist_route": ["settlement", "algebra"],
            },
            "snippet": "context-supported settlement signal",
        },
        {
            "id": "RECON-HUNT",
            "candidate_key": "CAND-HUNT",
            "status": "HUNT",
            "falsification": {"specialist_route": ["microstructure"]},
        },
        {
            "id": "RECON-NOISE",
            "candidate_key": "CAND-NOISE",
            "status": "DISCOVER",
            "falsification": {"specialist_route": ["behavioral"]},
        },
    ]}))

    out = m.apply_recon_watch_triage(packet_dir, recon_path)
    assert out["watch_count"] == 1
    assert out["specialist_roles"] == ["algebra", "settlement"]

    settlement = json.loads((packet_dir / "settlement.json").read_text())
    algebra = json.loads((packet_dir / "algebra.json").read_text())
    micro = json.loads((packet_dir / "microstructure.json").read_text())
    behavioral = json.loads((packet_dir / "behavioral.json").read_text())
    killer = json.loads((packet_dir / "prebuild_killer.json").read_text())

    for packet in [settlement, algebra]:
        triage = packet["recon_watch_triage"][0]
        assert triage["candidate_key"] == "CAND-WATCH"
        assert triage["status"] == "WATCH"
        assert triage["triage_only"] is True
        assert triage["promotion_authority"] is False
        assert triage["execution_gate"]["economic_conclusion"] == "NO_PROVEN_EDGE"
        assert triage["execution_gate"]["live_trading"] is False
        assert packet["status"] == "PENDING"

    assert "recon_watch_triage" not in micro
    assert "recon_watch_triage" not in behavioral
    assert "candidate_ids" not in killer
    assert "candidates" not in killer


def test_recon_watch_triage_deduplicates_same_candidate_per_role(tmp_path):
    m = load_module()
    m.ROOT = tmp_path
    packet_dir = tmp_path / "knowledge/runs/agent_packets/run"
    packet_dir.mkdir(parents=True)
    (packet_dir / "settlement.json").write_text(json.dumps({
        "agent_id": "settlement", "status": "PENDING", "input_refs": []
    }))
    recon_path = tmp_path / "knowledge/runs/recon/run.json"
    recon_path.parent.mkdir(parents=True)
    base = {
        "candidate_key": "CAND-X",
        "status": "WATCH",
        "attack_mode": "MECHANISM_BREAKER",
        "sources": [{"source_id": "a"}],
        "economic_model": {"public_trigger": "settlement"},
        "falsification": {"specialist_route": ["settlement"]},
    }
    recon_path.write_text(json.dumps({"findings": [
        dict(base, id="F1"),
        dict(base, id="F2"),
    ]}))
    out = m.apply_recon_watch_triage(packet_dir, recon_path)
    packet = json.loads((packet_dir / "settlement.json").read_text())
    assert out["watch_count"] == 2
    assert out["routed_items"] == 1
    assert len(packet["recon_watch_triage"]) == 1


def test_recon_hunt_routes_to_specialists_and_prebuild_killer(tmp_path):
    m=load_module()
    m.ROOT=tmp_path
    packet_dir=tmp_path/"knowledge/runs/agent_packets/run"
    packet_dir.mkdir(parents=True)
    for role in ["settlement","algebra","microstructure","prebuild_killer"]:
        (packet_dir/(role+".json")).write_text(json.dumps({"agent_id":role,"status":"PENDING","input_refs":[]}))
    hunt_path=tmp_path/"knowledge/runs/recon_hunts/run.json"
    hunt_path.parent.mkdir(parents=True)
    hunt_path.write_text(json.dumps({"plans":[{
        "candidate_id":"RECON-X",
        "status":"HUNT",
        "specialist_route":["settlement","algebra"],
        "execution_gate":{"research_only":True,"live_trading":False,"paid_actions":False,"wallet_actions":False}
    }]}))
    out=m.apply_recon_hunts(packet_dir,hunt_path)
    assert out["hunt_count"]==1
    settlement=json.loads((packet_dir/"settlement.json").read_text())
    algebra=json.loads((packet_dir/"algebra.json").read_text())
    micro=json.loads((packet_dir/"microstructure.json").read_text())
    killer=json.loads((packet_dir/"prebuild_killer.json").read_text())
    assert settlement["recon_hunts"][0]["candidate_id"]=="RECON-X"
    assert algebra["recon_hunts"][0]["candidate_id"]=="RECON-X"
    assert "recon_hunts" not in micro
    assert killer["candidate_ids"]==["RECON-X"]
    assert killer["candidates"][0]["candidate_id"]=="RECON-X"


def test_no_hunt_plan_is_noop(tmp_path):
    m=load_module()
    m.ROOT=tmp_path
    packet_dir=tmp_path/"packets"
    packet_dir.mkdir()
    assert m.apply_recon_hunts(packet_dir,None)["hunt_count"]==0


def test_no_recon_run_is_noop_for_watch_triage(tmp_path):
    m = load_module()
    m.ROOT = tmp_path
    packet_dir = tmp_path / "packets"
    packet_dir.mkdir()
    assert m.apply_recon_watch_triage(packet_dir, None)["watch_count"] == 0
