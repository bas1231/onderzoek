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


def test_six_domain_primary_with_evidence_is_ready():
    mod = load_module()
    for role in ("discovery", "market_research", "mechanics", "algebra"):
        d = mod.decide({
            "agent_id": role,
            "status": "PENDING",
            "input_refs": ["evidence.json"],
        })
        assert d.state == "READY"


def test_red_team_waits_without_candidate_and_runs_with_candidate():
    mod = load_module()
    waiting = mod.decide({
        "agent_id": "red_team_pentest",
        "status": "PENDING",
    })
    assert waiting.state == "WAITING_FOR_DATA"
    assert waiting.priority == "P2"

    ready = mod.decide({
        "agent_id": "red_team_pentest",
        "status": "PENDING",
        "candidate_ids": ["CAND-X"],
    })
    assert ready.state == "READY"
    assert ready.priority == "P2"


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
    (run / "discovery.json").write_text(json.dumps({
        "agent_id": "discovery",
        "status": "PENDING",
        "input_refs": ["routing.json"],
        "live_trading": True,
        "paid_actions": True,
        "wallet_actions": True,
        "openai_api": True,
    }))

    result = mod.orchestrate(run)
    packet = json.loads((run / "discovery.json").read_text())

    assert packet["status"] == "READY"
    assert packet["live_trading"] is False
    assert packet["paid_actions"] is False
    assert packet["wallet_actions"] is False
    assert packet["openai_api"] is False
    assert result["architecture"] == "E007_SIX_DOMAIN"
    for key in ("live_trading", "paid_actions", "wallet_actions", "openai_api"):
        assert result["guardrails"][key] is False


def test_red_team_requires_explicit_structured_pass(tmp_path):
    mod = load_module()
    run = tmp_path / "run"
    run.mkdir()
    (run / "red_team_pentest.json").write_text(json.dumps({
        "agent_id": "red_team_pentest",
        "status": "COMPLETED",
        "candidate_ids": ["X"],
        "notes": ["looks good"],
        "red_team_modes": {"X": "QUICK_KILL"},
    }))

    out = mod.propagate_validation(run)
    assert out["quick_kill_pass"] == []
    assert out["deep_falsification_pass"] == []
    assert out["reproduction_candidates"] == []
    assert out["proof_candidates"] == []
    assert out["economic_conclusion"] == "NO_PROVEN_EDGE"


def test_red_team_quick_and_deep_results_are_separate(tmp_path):
    mod = load_module()
    run = tmp_path / "run"
    run.mkdir()
    (run / "red_team_pentest.json").write_text(json.dumps({
        "agent_id": "red_team_pentest",
        "status": "COMPLETED",
        "red_team_modes": {
            "QUICK": "QUICK_KILL",
            "DEEP": "DEEP_FALSIFICATION",
        },
        "validation_results": [
            {"candidate_id": "QUICK", "status": "PASS", "mode": "QUICK_KILL"},
            {"candidate_id": "DEEP", "status": "PASS", "mode": "DEEP_FALSIFICATION"},
            {"candidate_id": "FAIL", "status": "FAIL", "mode": "QUICK_KILL"},
        ],
    }))

    out = mod.propagate_validation(run)
    assert out["quick_kill_pass"] == ["DEEP", "QUICK"]
    assert out["deep_falsification_pass"] == ["DEEP"]
    assert out["proof_candidates"] == []


def test_transient_reproducer_is_created_only_for_serious_candidate(tmp_path):
    mod = load_module()
    run = tmp_path / "run"
    run.mkdir()

    ordinary = {
        "queue": [{
            "candidate_id": "EARLY",
            "phase": "DISCOVERED",
            "queue_status": "NEEDS_DIRECTOR",
            "source_ref": "knowledge/candidates/EARLY.json",
        }]
    }
    assert mod.ensure_transient_reproducer(run, ordinary) == []
    assert not (run / "independent_reproducer.json").exists()

    serious = {
        "queue": [{
            "candidate_id": "SERIOUS",
            "phase": "PROMOTION",
            "queue_status": "PROMOTION_CANDIDATE",
            "open_question": "Can it reproduce?",
            "next_decisive_test": "blind replay",
            "source_ref": "knowledge/candidates/SERIOUS.json",
        }]
    }
    assert mod.ensure_transient_reproducer(run, serious) == ["SERIOUS"]
    packet = json.loads((run / "independent_reproducer.json").read_text())
    assert packet["transient"] is True
    assert packet["blind"] is True
    assert packet["originating_conclusions_withheld"] is True
    assert packet["reproduction_candidates"] == ["SERIOUS"]
    assert "finding" not in packet["blind_reproduction_interface"][0]


def test_reproducer_pass_without_full_proof_package_stays_unproven(tmp_path):
    mod = load_module()
    run = tmp_path / "run"
    run.mkdir()
    (run / "red_team_pentest.json").write_text(json.dumps({
        "red_team_modes": {"X": "DEEP_FALSIFICATION"},
        "validation_results": [
            {"candidate_id": "X", "status": "PASS", "mode": "DEEP_FALSIFICATION"}
        ],
    }))
    (run / "independent_reproducer.json").write_text(json.dumps({
        "reproduction_candidates": ["X"],
        "validation_results": [{"candidate_id": "X", "status": "PASS"}],
    }))
    out = mod.propagate_validation(run)
    assert out["proof_candidates"] == []
    assert out["economic_conclusion"] == "NO_PROVEN_EDGE"
    assert "missing_structured_gates" in out["proof_rejections"]["X"]


def test_complete_reproduced_proof_package_becomes_candidate_not_final_verdict(tmp_path):
    mod = load_module()
    run = tmp_path / "run"
    run.mkdir()
    (run / "red_team_pentest.json").write_text(json.dumps({
        "red_team_modes": {"X": "DEEP_FALSIFICATION"},
        "validation_results": [
            {"candidate_id": "X", "status": "PASS", "mode": "DEEP_FALSIFICATION"}
        ],
    }))
    gates = {gate: "PASS" for gate in mod.PROOF_GATES}
    economics = {
        "fees": 1,
        "spread": 1,
        "slippage": 1,
        "fills": "validated",
        "settlement": "validated",
        "capacity": "bounded",
        "net_edge": 0.01,
    }
    (run / "independent_reproducer.json").write_text(json.dumps({
        "reproduction_candidates": ["X"],
        "validation_results": [{
            "candidate_id": "X",
            "status": "PASS",
            "gates": gates,
            "economics": economics,
        }],
    }))

    out = mod.propagate_validation(run)
    assert out["proof_candidates"] == ["X"]
    assert out["economic_conclusion"] == "PROVEN_EDGE_CANDIDATE"


def test_orchestrate_rerun_skips_internal_summary(tmp_path):
    mod = load_module()
    run = tmp_path / "run"
    run.mkdir()
    (run / "discovery.json").write_text(json.dumps({
        "agent_id": "discovery",
        "status": "PENDING",
        "input_refs": ["routing.json"],
    }))

    first = mod.orchestrate(run)
    second = mod.orchestrate(run)

    assert len(first["queue"]) == 1
    assert len(second["queue"]) == 1
    assert second["queue"][0]["agent_id"] == "discovery"
    assert all(item["agent_id"] is not None for item in second["queue"])
    assert all(item["reason"] != "unknown_agent_role" for item in second["queue"])
