from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "control/hourly/scheduled_worker_contract.json"


def load_contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_local_runtime_is_optional_for_native_research():
    data = load_contract()
    policy = data["local_runtime_policy"]
    native = data["native_scheduled_research"]

    assert policy["required_for_native_research"] is False
    assert policy["manual_user_action_required"] is False
    assert native["enabled_when_local_runtime_unconfirmed"] is True
    assert data["local_exchange_request"]["browser_bridge_required"] is False


def test_runtime_health_states_distinguish_unknown_from_idle():
    data = load_contract()
    states = set(data["local_runtime_policy"]["states"])

    assert "LOCAL_RUNTIME_UNCONFIRMED" in states
    assert "LOCAL_RUNTIME_CONFIRMED_IDLE" in states
    assert "LOCAL_REQUEST_PENDING" in states
    assert "LOCAL_REQUEST_SERVICED" in states
    assert "LOCAL_EXCHANGE_BLOCKED" in states


def test_unconfirmed_runtime_never_blocks_research_or_requires_user_terminal():
    data = load_contract()
    policy = data["local_runtime_policy"]
    behavior = policy["behavior_when_unconfirmed"].lower()

    assert "continue native_scheduled_research" in behavior
    assert "never ask the user" in behavior
    assert "git pull" in behavior
    assert data["governor"]["live_trading"] is False
    assert data["governor"]["paid_actions"] is False
    assert data["governor"]["wallet_actions"] is False
    assert data["governor"]["openai_api"] is False
