import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path.cwd()


def load_module():
    path = ROOT / "control/hourly/ai_handoff.py"
    spec = importlib.util.spec_from_file_location(
        "ai_handoff_test",
        path,
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_compact_packet_preserves_decisive_fields():
    mod = load_module()

    triage = [{
        "candidate_key": "CAND-X",
        "status": "WATCH",
        "triage_only": True,
        "promotion_authority": False,
        "public_trigger": "settlement",
    }]
    hunts = [{
        "candidate_id": "RECON-HUNT-X",
        "status": "HUNT",
    }]

    x = mod.compact_packet({
        "agent_id": "algebra",
        "status": "READY",
        "priority": "P3",
        "routed_evidence": [{"source_id": "x"}],
        "recon_watch_triage": triage,
        "recon_hunts": hunts,
        "next_decisive_question": "Does identity hold?",
        "local_task_required": False,
        "live_trading": False,
    })

    assert x["agent_id"] == "algebra"
    assert x["status"] == "READY"
    assert x["routed_evidence"] == [{"source_id": "x"}]
    assert x["recon_watch_triage"] == triage
    assert x["recon_watch_triage"][0]["triage_only"] is True
    assert x["recon_watch_triage"][0]["promotion_authority"] is False
    assert x["recon_hunts"] == hunts
    assert x["next_decisive_question"] == "Does identity hold?"
    assert x["local_task_required"] is False


def test_ready_states_are_explicit():
    mod = load_module()
    assert mod.READY_STATES == {"READY", "RESULT_READY"}


def test_no_specialist_browser_fanout_source_policy():
    mod = load_module()

    source = (
        ROOT / "control/hourly/ai_handoff.py"
    ).read_text()

    assert '"single_chatgpt_turn": True' in source
    assert '"specialist_browser_requests": False' in source
    assert '"openai_api": False' in source
    assert '"watch_triage_is_not_promotion": True' in source
    assert '"watch_triage_promotion_authority": False' in source


def test_latest_real_bundle_if_available():
    mod = load_module()

    try:
        run_id = mod.latest_run_id()
    except RuntimeError:
        return

    handoff = (
        ROOT
        / "knowledge/runs"
        / f"{run_id}-director-handoff.json"
    )

    if not handoff.exists():
        return

    bundle, path = mod.build(run_id)

    assert path.exists()
    assert bundle["schema"] == "PVA_AI_WORK_BUNDLE_V1"
    assert bundle["guardrails"]["live_trading"] is False
    assert bundle["guardrails"]["paid_actions"] is False
    assert bundle["guardrails"]["wallet_actions"] is False
    assert bundle["guardrails"]["openai_api"] is False
    assert bundle["delivery_policy"]["single_chatgpt_turn"] is True
