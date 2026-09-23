import pytest

from control.hourly.ai_work_exchange import (
    ExchangeContractError,
    ROLE_CAPABILITIES,
    build_request,
    task_shape,
    validate_bundle,
)
from control.hourly.research_os_architecture import PERMANENT_AGENTS


def make_bundle(roles):
    return {
        "schema": "PVA_AI_WORK_BUNDLE_V1",
        "run_id": "hourly-role-contract-test",
        "response_token": "a" * 64,
        "ready_roles": [
            {
                "agent_id": role,
                "priority": "P3",
                "next_decisive_question": f"test {role}",
            }
            for role in roles
        ],
        "guardrails": {
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
            "openai_api": False,
        },
    }


def test_all_permanent_roles_supported():
    assert set(PERMANENT_AGENTS) <= set(ROLE_CAPABILITIES)


def test_all_six_roles_validate_and_build():
    roles = list(PERMANENT_AGENTS)
    b = make_bundle(roles)

    assert validate_bundle(b) is b

    req = build_request(b, source_commit="0" * 40)
    assert [x["agent_id"] for x in req["work_items"]] == roles


def test_unknown_role_fail_closed():
    with pytest.raises(ExchangeContractError, match="unsupported ready role"):
        validate_bundle(make_bundle(["definitely_not_a_role"]))


def test_task_shapes():
    assert task_shape("discovery") == "PARALLEL"
    assert task_shape("market_research") == "PARALLEL"
    assert task_shape("mechanics") == "SEQUENTIAL"
    assert task_shape("algebra") == "SEQUENTIAL"
    assert task_shape("red_team_pentest") == "PARTIAL"
    assert task_shape("research_director") == "PARTIAL"
