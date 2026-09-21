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

    # Test path needs to be relative to ROOT in production;
    # use a repository-local temporary fixture path instead.
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


def test_recon_hunt_routes_to_specialists_and_prebuild_killer(tmp_path):
    m=load(Path("control/hourly/packet_hydrator.py"))
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
    m=load(Path("control/hourly/packet_hydrator.py"))
    m.ROOT=tmp_path
    packet_dir=tmp_path/"packets"
    packet_dir.mkdir()
    assert m.apply_recon_hunts(packet_dir,None)["hunt_count"]==0
