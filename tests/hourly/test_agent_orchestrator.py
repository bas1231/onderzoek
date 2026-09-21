from pathlib import Path
import json
import importlib.util
import sys


ROOT = Path.cwd()


def load_module():
    path = ROOT / "control/hourly/agent_orchestrator.py"
    spec = importlib.util.spec_from_file_location(
        "agent_orchestrator",
        path,
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_primary_without_evidence_is_not_ready():
    mod = load_module()

    d = mod.decide({
        "agent_id": "algebra",
        "status": "PENDING",
        "input_refs": [],
        "notes": [],
    })

    assert d.state == "NO_EVIDENCE"
    assert d.priority == "P3"


def test_primary_with_evidence_is_ready():
    mod = load_module()

    d = mod.decide({
        "agent_id": "settlement",
        "status": "PENDING",
        "input_refs": ["evidence.json"],
    })

    assert d.state == "READY"


def test_falsifier_waits_without_survivor():
    mod = load_module()

    d = mod.decide({
        "agent_id": "chief_falsifier",
        "status": "PENDING",
    })

    assert d.state == "WAITING_FOR_DATA"
    assert d.priority == "P2"


def test_reproducer_waits_without_serious_survivor():
    mod = load_module()

    d = mod.decide({
        "agent_id": "independent_reproducer",
        "status": "PENDING",
    })

    assert d.state == "WAITING_FOR_DATA"


def test_director_is_ready():
    mod = load_module()

    d = mod.decide({
        "agent_id": "research_director",
        "status": "PENDING",
    })

    assert d.state == "READY"
    assert d.priority == "P1"


def test_guardrails_and_queue(tmp_path):
    mod = load_module()

    run = tmp_path / "run"
    run.mkdir()

    (run / "scout.json").write_text(json.dumps({
        "agent_id": "scout",
        "status": "PENDING",
        "input_refs": ["routing.json"],
        "live_trading": True,
        "paid_actions": True,
        "wallet_actions": True,
    }))

    result = mod.orchestrate(run)

    packet = json.loads(
        (run / "scout.json").read_text()
    )

    assert packet["status"] == "READY"
    assert packet["live_trading"] is False
    assert packet["paid_actions"] is False
    assert packet["wallet_actions"] is False

    assert result["guardrails"]["live_trading"] is False
    assert result["guardrails"]["paid_actions"] is False
    assert result["guardrails"]["wallet_actions"] is False


def test_validation_pipeline_requires_explicit_structured_pass(tmp_path):
    mod=load_module()
    run=tmp_path/"run"
    run.mkdir()
    (run/"prebuild_killer.json").write_text(json.dumps({"agent_id":"prebuild_killer","status":"COMPLETED","candidate_ids":["X"],"notes":["looks good"]}))
    (run/"chief_falsifier.json").write_text(json.dumps({"agent_id":"chief_falsifier","status":"WAITING_FOR_DATA"}))
    (run/"independent_reproducer.json").write_text(json.dumps({"agent_id":"independent_reproducer","status":"WAITING_FOR_DATA"}))
    out=mod.propagate_validation(run)
    assert out["killer_pass"]==[]
    assert json.loads((run/"chief_falsifier.json").read_text())["survivors"]==[]
    assert json.loads((run/"independent_reproducer.json").read_text())["reproduction_candidates"]==[]

def test_validation_pipeline_advances_only_same_candidate_through_both_gates(tmp_path):
    mod=load_module()
    run=tmp_path/"run"
    run.mkdir()
    (run/"prebuild_killer.json").write_text(json.dumps({"agent_id":"prebuild_killer","status":"COMPLETED","validation_results":[{"candidate_id":"X","status":"PASS"},{"candidate_id":"Y","status":"FAIL"}]}))
    (run/"chief_falsifier.json").write_text(json.dumps({"agent_id":"chief_falsifier","status":"COMPLETED","validation_results":[{"candidate_id":"X","status":"PASS"},{"candidate_id":"Z","status":"PASS"}]}))
    (run/"independent_reproducer.json").write_text(json.dumps({"agent_id":"independent_reproducer","status":"WAITING_FOR_DATA"}))
    out=mod.propagate_validation(run)
    assert out["killer_pass"]==["X"]
    assert out["falsifier_pass"]==["X","Z"]
    assert out["reproduction_candidates"]==["X"]
    assert out["economic_conclusion"]=="NO_PROVEN_EDGE"


def test_reproducer_pass_without_full_proof_package_stays_unproven(tmp_path):
    mod=load_module()
    run=tmp_path/"run"; run.mkdir()
    (run/"prebuild_killer.json").write_text(json.dumps({"validation_results":[{"candidate_id":"X","status":"PASS"}]}))
    (run/"chief_falsifier.json").write_text(json.dumps({"validation_results":[{"candidate_id":"X","status":"PASS"}]}))
    (run/"independent_reproducer.json").write_text(json.dumps({"validation_results":[{"candidate_id":"X","status":"PASS"}]}))
    out=mod.propagate_validation(run)
    assert out["proof_candidates"]==[]
    assert out["economic_conclusion"]=="NO_PROVEN_EDGE"
    assert "missing_structured_gates" in out["proof_rejections"]["X"]

def test_complete_reproduced_proof_package_becomes_candidate_not_final_verdict(tmp_path):
    mod=load_module()
    run=tmp_path/"run"; run.mkdir()
    (run/"prebuild_killer.json").write_text(json.dumps({"validation_results":[{"candidate_id":"X","status":"PASS"}]}))
    (run/"chief_falsifier.json").write_text(json.dumps({"validation_results":[{"candidate_id":"X","status":"PASS"}]}))
    gates={g:"PASS" for g in mod.PROOF_GATES}
    economics={"fees":1,"spread":1,"slippage":1,"fills":"validated","settlement":"validated","capacity":"bounded","net_edge":0.01}
    (run/"independent_reproducer.json").write_text(json.dumps({"validation_results":[{"candidate_id":"X","status":"PASS","gates":gates,"economics":economics}]}))
    out=mod.propagate_validation(run)
    assert out["proof_candidates"]==["X"]
    assert out["economic_conclusion"]=="PROVEN_EDGE_CANDIDATE"
