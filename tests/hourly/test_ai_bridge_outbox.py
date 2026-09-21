import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path.cwd()


def load_bridge():
    control = ROOT / "control"

    if str(control) not in sys.path:
        sys.path.insert(0, str(control))

    path = control / "browser_bridge.py"

    spec = importlib.util.spec_from_file_location(
        "browser_bridge_ai_test",
        path,
    )

    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)

    return mod


def core_source():
    return (
        ROOT / "control/browser_bridge_core.py"
    ).read_text()


def test_dedicated_routes_exist():
    source = core_source()

    assert 'path == "/ai-outbox"' in source
    assert 'path == "/ai-ack"' in source


def test_hourly_wake_excluded_from_normal_outbox():
    source = core_source()

    assert (
        'incident.get("reason")'
        in source
    )

    assert "HOURLY_RESEARCH_WAKE" in source


def test_ai_item_never_has_executor_fields(
    tmp_path,
    monkeypatch,
):
    mod = load_bridge()

    incident_dir = (
        tmp_path
        / ".local/state/prediction-research/incidents"
    )
    incident_dir.mkdir(parents=True)

    incident = {
        "task_id":
            "hourly-research-20260920T1700+0200",
        "reason": "HOURLY_RESEARCH_WAKE",
        "status": "OPEN",
        "deliver_to_chat": True,
    }

    p = (
        incident_dir
        / (
            "hourly-research-20260920T1700+0200"
            "__HOURLY_RESEARCH_WAKE.json"
        )
    )

    p.write_text(json.dumps(incident))

    monkeypatch.setattr(
        Path,
        "home",
        classmethod(lambda cls: tmp_path),
    )

    monkeypatch.setattr(
        mod,
        "load_state",
        lambda: {
            "bridge_tasks": [],
            "acked": [],
            "ai_acked": [],
        },
    )

    item = {
        "kind": "AI_WORK_BUNDLE",
        "task_id": incident["task_id"],
        "guardrails": {
            "direct_executor_route": False,
        },
    }

    monkeypatch.setattr(
        mod.AI_TRANSPORT,
        "should_offer_ai_work",
        lambda x: True,
    )

    monkeypatch.setattr(
        mod.AI_TRANSPORT,
        "build_chat_item",
        lambda x: item,
    )

    result = mod.next_ai_outbox_item()

    assert result == item

    forbidden = {
        "command",
        "shell",
        "argv",
        "exec",
        "executable",
    }

    assert not forbidden.intersection(result)


def test_ai_ack_is_separate_in_source():
    source = core_source()

    assert 'state.get("ai_acked", [])' in source
    assert 'state.setdefault(' in source
    assert '"ai_acked"' in source


def test_response_route_is_not_generic_executor_route():
    wrapper = (
        ROOT / "control/browser_bridge.py"
    ).read_text()
    assert 'path != "/ai-response"' in wrapper
    assert "AI_RESPONSE_RECEIVER.receive" in wrapper
    assert '"/enqueue"' not in wrapper
