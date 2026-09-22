import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path.cwd()


def load_module():
    path = ROOT / "control/hourly/ai_response.py"
    spec = importlib.util.spec_from_file_location(
        "ai_response_test",
        path,
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def base_response(run_id="hourly-test"):
    return {
        "schema": "PVA_AI_RESPONSE_V1",
        "run_id": run_id,
        "role_results": [
            {
                "agent_id": "discovery",
                "status": "COMPLETED",
                "finding": "No decisive new evidence.",
                "evidence_refs": [],
                "candidate_ids": [],
                "capability_results": {
                    "scout": {"finding": "no decisive evidence"},
                    "recon_scout": {"finding": "no decisive evidence"},
                },
                "validation_results": [],
                "failure_pattern_ids": [],
                "next_decisive_question": None,
                "local_task_required": False,
                "local_task_spec": None,
            }
        ],
        "candidate_decisions": [],
        "director_decision": "Continue falsification.",
        "economic_conclusion": "NO_PROVEN_EDGE",
        "local_tasks": [],
    }


def test_valid_response():
    mod = load_module()
    x = base_response()
    assert mod.validate_response(x, "hourly-test") == x


def test_wrong_schema_rejected():
    mod = load_module()
    x = base_response()
    x["schema"] = "OTHER"
    with pytest.raises(mod.ValidationError, match="schema"):
        mod.validate_response(x, "hourly-test")


def test_wrong_run_rejected():
    mod = load_module()
    x = base_response()
    with pytest.raises(mod.ValidationError):
        mod.validate_response(x, "other-run")


def test_edge_claim_rejected():
    mod = load_module()
    x = base_response()
    x["economic_conclusion"] = "PROVEN_EDGE"
    with pytest.raises(mod.ValidationError):
        mod.validate_response(x, "hourly-test")


def test_paid_action_rejected():
    mod = load_module()
    x = base_response()
    x["paid_actions"] = True
    with pytest.raises(mod.ValidationError):
        mod.validate_response(x, "hourly-test")


def test_direct_command_in_role_task_rejected():
    mod = load_module()
    x = base_response()
    x["role_results"][0]["local_task_required"] = True
    x["role_results"][0]["local_task_spec"] = {
        "question": "test something",
        "command": "rm -rf /",
    }
    with pytest.raises(mod.ValidationError):
        mod.validate_response(x, "hourly-test")


def test_direct_command_in_local_tasks_rejected():
    mod = load_module()
    x = base_response()
    x["local_tasks"] = [
        {"task_id": "x", "command": ["python", "x.py"]}
    ]
    with pytest.raises(mod.ValidationError):
        mod.validate_response(x, "hourly-test")


def test_unknown_or_legacy_permanent_role_rejected():
    mod = load_module()
    for invalid in ("fake_agent", "scout", "weather_twc", "prebuild_killer"):
        x = base_response()
        x["role_results"][0]["agent_id"] = invalid
        with pytest.raises(mod.ValidationError):
            mod.validate_response(x, "hourly-test")


def test_invalid_candidate_state_rejected():
    mod = load_module()
    x = base_response()
    x["candidate_decisions"] = [
        {
            "candidate_id": "ABC",
            "queue_status": "PROVEN",
            "reason": "bad",
        }
    ]
    with pytest.raises(mod.ValidationError):
        mod.validate_response(x, "hourly-test")


def test_invalid_failure_pattern_rejected():
    mod = load_module()
    x = base_response()
    x["role_results"][0]["failure_pattern_ids"] = ["FP-999"]
    with pytest.raises(mod.ValidationError):
        mod.validate_response(x, "hourly-test")


def test_path_traversal_candidate_rejected():
    mod = load_module()
    with pytest.raises(mod.ValidationError):
        mod.candidate_path("../../etc/passwd")
