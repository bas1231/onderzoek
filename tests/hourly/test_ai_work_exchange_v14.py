import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path.cwd()
TOKEN = "a" * 64


def load_module():
    path = ROOT / "control/hourly/ai_work_exchange.py"
    spec = importlib.util.spec_from_file_location("ai_work_exchange_v14_test", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def bundle(roles):
    return {
        "schema": "PVA_AI_WORK_BUNDLE_V1",
        "run_id": "hourly-20260921T210000+0200",
        "response_token": TOKEN,
        "guardrails": {
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
            "openai_api": False,
        },
        "ready_roles": [
            {
                "agent_id": role,
                "status": "READY",
                "priority": "P3",
                "next_decisive_question": f"question for {role}",
            }
            for role in roles
        ],
        "candidate_queue": {
            "director_attention": [],
            "waiting_without_blocking": [],
            "full_queue": [],
        },
        "director_instruction": "research only",
        "expected_response_schema": {
            "schema": "PVA_AI_RESPONSE_V1"
        },
    }


def test_legacy_roles_map_to_research_os_capabilities():
    mod = load_module()
    request = mod.build_request(
        bundle([
            "recon_scout",
            "settlement",
            "algebra",
            "chief_falsifier",
            "research_director",
        ]),
        source_commit="1" * 40,
    )

    items = {item["agent_id"]: item for item in request["work_items"]}
    assert items["recon_scout"]["responsibility"] == "RECON_SCOUT"
    assert items["settlement"]["capability_mode"] == "MECHANICS"
    assert items["algebra"]["capability_mode"] == "ALGEBRA"
    assert items["chief_falsifier"]["responsibility"] == "RED_TEAM"
    assert items["research_director"]["responsibility"] == "RESEARCH_DIRECTOR"
    assert request["transport"]["browser_bridge_required"] is False
    assert request["transport"]["preferred_transport"] == "git"
    assert request["governor"]["economic_conclusion"] == "NO_PROVEN_EDGE"
    assert request["governor"]["watch_has_no_promotion_authority"] is True
    assert request["governor"]["live_trading"] is False
    assert request["governor"]["paid_actions"] is False
    assert request["governor"]["wallet_actions"] is False


def test_request_hash_detects_tampering():
    mod = load_module()
    request = mod.build_request(bundle(["settlement"]), source_commit="2" * 40)
    assert mod.validate_request(request) is request

    tampered = json.loads(json.dumps(request))
    tampered["work_items"][0]["capability_mode"] = "MARKET_RESEARCH"
    with pytest.raises(mod.ExchangeContractError):
        mod.validate_request(tampered)


def test_bundle_requires_all_hard_guardrails_false():
    mod = load_module()
    unsafe = bundle(["settlement"])
    unsafe["guardrails"]["paid_actions"] = True
    with pytest.raises(mod.ExchangeContractError, match="paid_actions"):
        mod.build_request(unsafe, source_commit="3" * 40)


def test_work_ids_are_deterministic_and_unique_per_role():
    mod = load_module()
    request_a = mod.build_request(
        bundle(["settlement", "algebra"]),
        source_commit="4" * 40,
    )
    request_b = mod.build_request(
        bundle(["settlement", "algebra"]),
        source_commit="4" * 40,
    )
    ids_a = [item["work_id"] for item in request_a["work_items"]]
    ids_b = [item["work_id"] for item in request_b["work_items"]]
    assert ids_a == ids_b
    assert len(ids_a) == len(set(ids_a))


def test_empty_ready_set_is_valid_no_work_request():
    mod = load_module()
    request = mod.build_request(bundle([]), source_commit="5" * 40)
    assert request["work_items"] == []
    mod.validate_request(request)
