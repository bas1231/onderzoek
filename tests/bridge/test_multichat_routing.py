from pathlib import Path
from types import SimpleNamespace
import importlib
import json
import sys


def load_bridge():
    root = Path(__file__).resolve().parents[2]
    control = root / "control"
    if str(control) not in sys.path:
        sys.path.insert(0, str(control))
    sys.modules.pop("browser_bridge", None)
    return importlib.import_module("browser_bridge")


def write_result(root: Path, task_id: str):
    result_dir = root / task_id
    result_dir.mkdir(parents=True)
    (result_dir / "RESULT.json").write_text(
        json.dumps({"task_id": task_id, "status": "completed"}),
        encoding="utf-8",
    )
    (result_dir / "stdout.log").write_text("ok", encoding="utf-8")
    (result_dir / "stderr.log").write_text("", encoding="utf-8")


def test_results_are_routed_to_originating_chat(tmp_path, monkeypatch):
    bb = load_bridge()
    results = tmp_path / "results"
    write_result(results, "TASK-A")
    write_result(results, "TASK-B")

    state = {
        "bridge_tasks": ["TASK-A", "TASK-B"],
        "acked": [],
        "task_clients": {
            "TASK-A": "chat-a",
            "TASK-B": "chat-b",
        },
    }

    monkeypatch.setattr(bb, "RESULTS", results)
    monkeypatch.setattr(bb, "load_state", lambda: state)
    monkeypatch.setattr(bb, "save_state", lambda new_state: None)
    monkeypatch.setattr(bb, "lifecycle_load", lambda task_id: {"state": None})
    monkeypatch.setattr(bb, "lifecycle_update", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        bb,
        "git",
        lambda *args, **kwargs: SimpleNamespace(stdout="abc123\n", returncode=0),
    )
    monkeypatch.setattr(bb, "_next_incident_item", lambda *args, **kwargs: None)

    item_a = bb.next_outbox_item("chat-a", "chat-a-tab-1")
    item_b = bb.next_outbox_item("chat-b", "chat-b-tab-2")
    legacy = bb.next_outbox_item()

    assert item_a["task_id"] == "TASK-A"
    assert item_b["task_id"] == "TASK-B"
    assert legacy is None
    assert state["result_delivery_leases"]["TASK-A"]["consumer_id"] == "chat-a-tab-1"
    assert state["result_delivery_leases"]["TASK-B"]["consumer_id"] == "chat-b-tab-2"


def test_wrong_chat_cannot_ack_routed_result(monkeypatch):
    bb = load_bridge()
    state = {
        "bridge_tasks": ["TASK-A"],
        "acked": [],
        "task_clients": {"TASK-A": "chat-a"},
        "result_delivery_leases": {
            "TASK-A": {
                "client_id": "chat-a",
                "consumer_id": "chat-a-tab-1",
                "lease_until": 9999999999,
            }
        },
    }

    monkeypatch.setattr(bb, "load_state", lambda: state)
    monkeypatch.setattr(bb, "save_state", lambda new_state: None)
    monkeypatch.setattr(bb, "_core_acknowledge", lambda task_id: {"ok": True, "task_id": task_id})
    monkeypatch.setattr(bb, "_resolve_incident_after_ack", lambda task_id: False)
    monkeypatch.setattr(bb, "_queue_control_continue", lambda *args, **kwargs: False)

    wrong = bb.acknowledge("TASK-A", "chat-b")
    right = bb.acknowledge("TASK-A", "chat-a")

    assert wrong["ok"] is False
    assert wrong["reason"] == "RESULT_CLIENT_MISMATCH"
    assert right["ok"] is True
    assert "TASK-A" not in state["result_delivery_leases"]


def test_same_chat_duplicate_tabs_are_delivery_leased(tmp_path, monkeypatch):
    bb = load_bridge()
    results = tmp_path / "results"
    write_result(results, "TASK-A")

    state = {
        "bridge_tasks": ["TASK-A"],
        "acked": [],
        "task_clients": {"TASK-A": "chat-a"},
    }

    monkeypatch.setattr(bb, "RESULTS", results)
    monkeypatch.setattr(bb, "load_state", lambda: state)
    monkeypatch.setattr(bb, "save_state", lambda new_state: None)
    monkeypatch.setattr(bb, "lifecycle_load", lambda task_id: {"state": None})
    monkeypatch.setattr(bb, "lifecycle_update", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        bb,
        "git",
        lambda *args, **kwargs: SimpleNamespace(stdout="abc123\n", returncode=0),
    )
    monkeypatch.setattr(bb, "_next_incident_item", lambda *args, **kwargs: None)

    first = bb.next_outbox_item("chat-a", "chat-a-tab-1")
    second = bb.next_outbox_item("chat-a", "chat-a-tab-2")

    assert first["task_id"] == "TASK-A"
    assert second is None


def test_ai_work_is_leased_to_one_chat(monkeypatch):
    bb = load_bridge()
    state = {"ai_acked": []}
    item = {
        "kind": "AI_WORK_BUNDLE",
        "task_id": "AI-WORK-1",
        "bundle": {},
        "guardrails": {"direct_executor_route": False},
    }

    monkeypatch.setattr(bb, "load_state", lambda: state)
    monkeypatch.setattr(bb, "save_state", lambda new_state: None)
    monkeypatch.setattr(bb, "_stalled_ai_retry", lambda new_state: None)
    monkeypatch.setattr(bb, "_core_next_ai_outbox_item", lambda: item)
    monkeypatch.setattr(bb, "_core_acknowledge_ai", lambda task_id: {"ok": True, "task_id": task_id})

    first = bb.next_ai_outbox_item("chat-a", "chat-a-tab-1")
    other = bb.next_ai_outbox_item("chat-b", "chat-b-tab-2")
    wrong_ack = bb.acknowledge_ai("AI-WORK-1", "chat-b", "chat-b-tab-2")
    right_ack = bb.acknowledge_ai("AI-WORK-1", "chat-a", "chat-a-tab-1")

    assert first["task_id"] == "AI-WORK-1"
    assert other is None
    assert wrong_ack["ok"] is False
    assert wrong_ack["reason"] == "AI_CLIENT_MISMATCH"
    assert right_ack["ok"] is True
    assert "AI-WORK-1" not in state.get("ai_delivery_leases", {})


def test_control_continue_prefers_source_chat(monkeypatch):
    bb = load_bridge()
    state = {
        "ai_acked": [],
        "task_clients": {"TASK-A": "chat-a"},
    }
    item = {
        "kind": "AI_WORK_BUNDLE",
        "task_id": "CONTINUE-A",
        "bundle": {"source_task_id": "TASK-A"},
        "guardrails": {"direct_executor_route": False},
    }

    monkeypatch.setattr(bb, "load_state", lambda: state)
    monkeypatch.setattr(bb, "save_state", lambda new_state: None)
    monkeypatch.setattr(bb, "_stalled_ai_retry", lambda new_state: None)
    monkeypatch.setattr(bb, "_core_next_ai_outbox_item", lambda: item)

    assert bb.next_ai_outbox_item("chat-b", "chat-b-tab-2") is None
    assert bb.next_ai_outbox_item("chat-a", "chat-a-tab-1")["task_id"] == "CONTINUE-A"
