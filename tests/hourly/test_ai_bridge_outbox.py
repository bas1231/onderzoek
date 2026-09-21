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


def _write_hourly_incident(tmp_path, task_id):
    incident_dir = (
        tmp_path
        / ".local/state/prediction-research/incidents"
    )
    incident_dir.mkdir(parents=True, exist_ok=True)
    incident = {
        "task_id": task_id,
        "reason": "HOURLY_RESEARCH_WAKE",
        "status": "OPEN",
        "deliver_to_chat": True,
    }
    path = incident_dir / (task_id + "__HOURLY_RESEARCH_WAKE.json")
    path.write_text(json.dumps(incident))
    return incident


def test_stalled_ai_delivery_is_reoffered_after_timeout(
    tmp_path,
    monkeypatch,
):
    mod = load_bridge()
    task_id = "hourly-research-20260920T1700+0200"
    incident = _write_hourly_incident(tmp_path, task_id)
    state = {
        "bridge_tasks": [],
        "acked": [],
        "ai_acked": [task_id],
        "ai_deliveries": {
            task_id: {
                "last_acked_at": 1000.0,
                "attempts": 1,
            }
        },
    }
    item = {
        "kind": "AI_WORK_BUNDLE",
        "task_id": task_id,
        "guardrails": {"direct_executor_route": False},
    }

    monkeypatch.setattr(
        Path,
        "home",
        classmethod(lambda cls: tmp_path),
    )
    monkeypatch.setattr(mod, "load_state", lambda: state)
    monkeypatch.setattr(mod, "_core_next_ai_outbox_item", lambda: None)
    monkeypatch.setattr(mod.time, "time", lambda: 1601.0)
    monkeypatch.setattr(
        mod.AI_TRANSPORT,
        "should_offer_ai_work",
        lambda x: x == incident,
    )
    monkeypatch.setattr(
        mod.AI_TRANSPORT,
        "build_chat_item",
        lambda x: item,
    )

    assert mod.next_ai_outbox_item() == item


def test_fresh_or_legacy_ai_ack_is_not_replayed(
    tmp_path,
    monkeypatch,
):
    mod = load_bridge()
    task_id = "hourly-research-20260920T1700+0200"
    _write_hourly_incident(tmp_path, task_id)

    monkeypatch.setattr(
        Path,
        "home",
        classmethod(lambda cls: tmp_path),
    )
    monkeypatch.setattr(mod, "_core_next_ai_outbox_item", lambda: None)
    monkeypatch.setattr(mod.time, "time", lambda: 1601.0)
    monkeypatch.setattr(
        mod.AI_TRANSPORT,
        "should_offer_ai_work",
        lambda x: True,
    )

    fresh = {
        "ai_acked": [task_id],
        "ai_deliveries": {
            task_id: {
                "last_acked_at": 1501.0,
                "attempts": 1,
            }
        },
    }
    monkeypatch.setattr(mod, "load_state", lambda: fresh)
    assert mod.next_ai_outbox_item() is None

    legacy = {"ai_acked": [task_id]}
    monkeypatch.setattr(mod, "load_state", lambda: legacy)
    assert mod.next_ai_outbox_item() is None


def test_response_or_receipt_suppresses_stalled_retry(
    tmp_path,
    monkeypatch,
):
    mod = load_bridge()
    task_id = "hourly-research-20260920T1700+0200"
    _write_hourly_incident(tmp_path, task_id)
    state = {
        "ai_acked": [task_id],
        "ai_deliveries": {
            task_id: {
                "last_acked_at": 1000.0,
                "attempts": 1,
            }
        },
    }

    monkeypatch.setattr(
        Path,
        "home",
        classmethod(lambda cls: tmp_path),
    )
    monkeypatch.setattr(mod, "load_state", lambda: state)
    monkeypatch.setattr(mod, "_core_next_ai_outbox_item", lambda: None)
    monkeypatch.setattr(mod.time, "time", lambda: 1601.0)
    monkeypatch.setattr(
        mod.AI_TRANSPORT,
        "should_offer_ai_work",
        lambda x: False,
    )

    assert mod.next_ai_outbox_item() is None


def test_ai_ack_records_delivery_without_refreshing_duplicate(
    monkeypatch,
):
    mod = load_bridge()
    task_id = "hourly-research-20260920T1700+0200"
    state = {
        "ai_acked": [task_id],
        "ai_deliveries": {},
    }
    saved = []

    monkeypatch.setattr(mod, "load_state", lambda: state)
    monkeypatch.setattr(mod, "save_state", lambda x: saved.append(dict(x)))
    monkeypatch.setattr(mod.time, "time", lambda: 1234.0)
    monkeypatch.setattr(
        mod,
        "_core_acknowledge_ai",
        lambda x: {"ok": True, "task_id": x},
    )

    first = mod.acknowledge_ai(task_id)
    assert first["ok"] is True
    assert state["ai_deliveries"][task_id] == {
        "last_acked_at": 1234.0,
        "attempts": 1,
    }
    assert saved

    monkeypatch.setattr(mod.time, "time", lambda: 1300.0)
    monkeypatch.setattr(
        mod,
        "_core_acknowledge_ai",
        lambda x: {
            "ok": True,
            "task_id": x,
            "already_acked": True,
        },
    )

    second = mod.acknowledge_ai(task_id)
    assert second["already_acked"] is True
    assert state["ai_deliveries"][task_id]["last_acked_at"] == 1234.0
    assert state["ai_deliveries"][task_id]["attempts"] == 1
