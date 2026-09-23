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


def test_response_token_is_deterministic_and_work_bound():
    mod = load_module()
    roles = [{"agent_id": "algebra", "status": "READY"}]
    queue = {"director_attention": [], "full_queue": []}

    a = mod.response_token("hourly-test", roles, queue)
    b = mod.response_token("hourly-test", roles, queue)
    changed = mod.response_token(
        "hourly-test",
        roles + [{"agent_id": "settlement", "status": "READY"}],
        queue,
    )

    assert a == b
    assert len(a) == 64
    assert set(a) <= set("0123456789abcdef")
    assert changed != a


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
    assert len(bundle["response_token"]) == 64
    assert (
        bundle["expected_response_schema"]["schema"]
        == "PVA_AI_RESPONSE_V1"
    )
    assert (
        bundle["expected_response_schema"]["response_token"]
        == bundle["response_token"]
    )
    assert bundle["guardrails"]["live_trading"] is False
    assert bundle["guardrails"]["paid_actions"] is False
    assert bundle["guardrails"]["wallet_actions"] is False
    assert bundle["guardrails"]["openai_api"] is False
    assert bundle["delivery_policy"]["single_chatgpt_turn"] is True



def test_build_reuses_first_bundle_for_same_run_id(tmp_path):
    mod = load_module()

    mod.RUNS = tmp_path / "runs"
    mod.PACKETS = mod.RUNS / "agent_packets"

    run_id = "hourly-20990101T120000+0200"
    packet_dir = mod.PACKETS / run_id
    packet_dir.mkdir(parents=True)

    handoff = {
        "director_attention": [],
        "waiting_without_blocking": [],
        "full_queue": [],
    }
    (
        mod.RUNS / f"{run_id}-director-handoff.json"
    ).write_text(
        json.dumps(handoff),
        encoding="utf-8",
    )

    first_packet = {
        "run_id": run_id,
        "agent_id": "discovery",
        "status": "READY",
        "priority": "P3",
        "candidate_ids": [],
        "next_decisive_question": "first question",
    }
    (
        packet_dir / "discovery.json"
    ).write_text(
        json.dumps(first_packet),
        encoding="utf-8",
    )

    first, first_path = mod.build(run_id)

    changed_packet = dict(first_packet)
    changed_packet["next_decisive_question"] = "changed later"
    (
        packet_dir / "discovery.json"
    ).write_text(
        json.dumps(changed_packet),
        encoding="utf-8",
    )

    second, second_path = mod.build(run_id)

    assert second_path == first_path
    assert second == first
    assert second["response_token"] == first["response_token"]
    assert (
        second["ready_roles"][0]["next_decisive_question"]
        == "first question"
    )
