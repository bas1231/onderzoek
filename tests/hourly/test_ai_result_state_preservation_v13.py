import importlib.util
import sys
from pathlib import Path


ROOT = Path.cwd()


def load_orchestrator():
    path = ROOT / "control/hourly/agent_orchestrator.py"
    spec = importlib.util.spec_from_file_location(
        "ai_result_state_orchestrator",
        path,
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_pre_worker_no_evidence_can_be_reopened_by_evidence():
    mod = load_orchestrator()
    decision = mod.decide({
        "agent_id": "recon_scout",
        "status": "NO_EVIDENCE",
        "input_refs": ["new-evidence.json"],
        "priority": "P3",
    })
    assert decision.state == "READY"


def test_worker_no_evidence_is_terminal_for_same_run():
    mod = load_orchestrator()
    decision = mod.decide({
        "agent_id": "recon_scout",
        "status": "NO_EVIDENCE",
        "input_refs": ["old-evidence.json"],
        "priority": "P3",
        "ai_result": {
            "finding": "Evidence checked; no supported anomaly.",
            "evidence_refs": ["old-evidence.json"],
        },
    })
    assert decision.state == "NO_EVIDENCE"
    assert decision.reason == "ai_result_preserved"
