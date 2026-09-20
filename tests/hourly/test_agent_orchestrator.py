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
