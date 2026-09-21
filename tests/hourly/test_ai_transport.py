import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path.cwd()
TOKEN = "a" * 64


def load_module():
    path = ROOT / "control/hourly/ai_transport.py"
    spec = importlib.util.spec_from_file_location(
        "ai_transport_test",
        path,
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def incident():
    return {
        "task_id": "hourly-research-20260920T1700+0200",
        "reason": "HOURLY_RESEARCH_WAKE",
        "status": "OPEN",
        "deliver_to_chat": True,
    }


def bundle(run_id):
    return {
        "schema": "PVA_AI_WORK_BUNDLE_V1",
        "run_id": run_id,
        "response_token": TOKEN,
        "delivery_policy": {
            "single_chatgpt_turn": True,
        },
        "guardrails": {
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
            "openai_api": False,
        },
    }


def test_run_id_conversion():
    mod = load_module()
    assert mod.run_id_from_incident(incident()) == (
        "hourly-20260920T170000+0200"
    )


def test_non_hourly_incident_rejected():
    mod = load_module()
    x = incident()
    x["reason"] = "OTHER"

    with pytest.raises(mod.TransportError):
        mod.run_id_from_incident(x)


def test_closed_incident_rejected():
    mod = load_module()
    x = incident()
    x["status"] = "DELIVERED"

    with pytest.raises(mod.TransportError):
        mod.build_chat_item(x)


def test_not_deliverable_rejected():
    mod = load_module()
    x = incident()
    x["deliver_to_chat"] = False

    with pytest.raises(mod.TransportError):
        mod.build_chat_item(x)


def test_path_traversal_rejected():
    mod = load_module()

    with pytest.raises(mod.TransportError):
        mod.safe_run_id("hourly-../../etc/passwd")


def test_chat_item_has_no_executor_fields(tmp_path, monkeypatch):
    mod = load_module()

    runs = tmp_path / "knowledge/runs"
    runs.mkdir(parents=True)

    run_id = "hourly-20260920T170000+0200"

    (
        runs / f"{run_id}-ai-work-bundle.json"
    ).write_text(json.dumps(bundle(run_id)))

    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(mod, "RUNS", runs)

    item = mod.build_chat_item(
        incident(),
        run_id=run_id,
    )

    forbidden = {
        "command",
        "shell",
        "argv",
        "exec",
        "executable",
    }

    assert not forbidden.intersection(item)
    assert item["kind"] == "AI_WORK_BUNDLE"
    assert item["guardrails"]["direct_executor_route"] is False
    assert item["response_contract"]["response_token"] == TOKEN
    assert item["response_contract"]["marker_start"] == mod.AI_RESPONSE_START
    assert item["response_contract"]["marker_end"] == mod.AI_RESPONSE_END


def test_missing_response_token_rejected(tmp_path, monkeypatch):
    mod = load_module()
    runs = tmp_path / "knowledge/runs"
    runs.mkdir(parents=True)
    run_id = "hourly-20260920T170000+0200"
    bad = bundle(run_id)
    bad.pop("response_token")
    (runs / f"{run_id}-ai-work-bundle.json").write_text(json.dumps(bad))
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(mod, "RUNS", runs)

    with pytest.raises(mod.TransportError, match="response_token"):
        mod.build_chat_item(incident(), run_id=run_id)


def test_existing_response_suppresses_duplicate(tmp_path, monkeypatch):
    mod = load_module()

    runs = tmp_path / "knowledge/runs"
    runs.mkdir(parents=True)

    run_id = "hourly-20260920T170000+0200"

    (
        runs / f"{run_id}-ai-work-bundle.json"
    ).write_text(json.dumps(bundle(run_id)))

    (
        runs / f"{run_id}-ai-response.json"
    ).write_text("{}")

    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(mod, "RUNS", runs)

    assert mod.should_offer_ai_work(
        incident(),
        run_id=run_id,
    ) is False
