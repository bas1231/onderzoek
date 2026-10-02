from pathlib import Path
import importlib
import json
import sys


def load_overlay():
    root = Path(__file__).resolve().parents[2]
    module_dir = root / "control" / "tampermonkey_multichat"
    if str(module_dir) not in sys.path:
        sys.path.insert(0, str(module_dir))
    for name in (
        "bridge_server_continuation",
        "bridge_server_status_compaction",
        "bridge_server_session_bootstrap",
        "bridge_server_hardened",
        "bridge_server_v2",
        "continuation_manager",
    ):
        sys.modules.pop(name, None)
    return importlib.import_module("bridge_server_continuation")


def test_sent_ack_hook_creates_exactly_one_continuation(tmp_path, monkeypatch):
    mod = load_overlay()
    base = mod.base
    data = tmp_path / "bridge"
    sent = data / "sent"
    routes = data / "routes"
    outbox = data / "outbox"
    states = tmp_path / "task-state"
    for path in (sent, routes, outbox, states):
        path.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(base, "DATA_DIR", data)
    monkeypatch.setattr(base, "SENT", sent)
    monkeypatch.setattr(base, "ROUTES", routes)
    monkeypatch.setattr(base, "OUTBOX", outbox)
    monkeypatch.setattr(mod, "TASK_STATE_DIR", states)

    source = "ACK-HOOK-SOURCE-001"
    event_id = "event-ack-hook-001"
    (states / f"{source}.json").write_text(json.dumps({
        "schema": "PREDICTION_COMMAND_BUS_TASK_STATE_V1",
        "task_id": source,
        "status": "DISPATCHED",
        "auto_continue": True,
    }), encoding="utf-8")
    (routes / f"{source}.json").write_text(json.dumps({
        "version": 2,
        "task_id": source,
        "chat_id": "chat-ack-hook-001",
        "consumer_id": None,
    }), encoding="utf-8")
    (sent / f"{event_id}.json").write_text(json.dumps({
        "event_id": event_id,
        "task_id": source,
        "message": "NIGHTSHIFT_WSL_RESULT_V1 task=ACK-HOOK-SOURCE-001 status=PASS exit=0",
    }), encoding="utf-8")

    mod.continuation_release_lease(event_id)
    records = list((data / "continuations").glob("CONT-*.json"))
    assert len(records) == 1
    first = json.loads(records[0].read_text(encoding="utf-8"))
    assert first["source_task_id"] == source
    assert first["chat_id"] == "chat-ack-hook-001"
    assert first["state"] == "CONTINUE_REQUESTED"

    # Duplicate /ack or process-level replay is idempotent.
    mod.continuation_release_lease(event_id)
    records2 = list((data / "continuations").glob("CONT-*.json"))
    assert len(records2) == 1
    second = json.loads(records2[0].read_text(encoding="utf-8"))
    assert second["continuation_id"] == first["continuation_id"]


def test_sent_ack_hook_ignores_normal_tasks(tmp_path, monkeypatch):
    mod = load_overlay()
    base = mod.base
    data = tmp_path / "bridge"
    sent = data / "sent"
    routes = data / "routes"
    states = tmp_path / "task-state"
    for path in (sent, routes, states):
        path.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(base, "DATA_DIR", data)
    monkeypatch.setattr(base, "SENT", sent)
    monkeypatch.setattr(base, "ROUTES", routes)
    monkeypatch.setattr(mod, "TASK_STATE_DIR", states)

    source = "ACK-HOOK-NORMAL-001"
    event_id = "event-ack-hook-normal-001"
    (states / f"{source}.json").write_text(json.dumps({
        "task_id": source,
        "status": "DISPATCHED",
        "auto_continue": False,
    }), encoding="utf-8")
    (routes / f"{source}.json").write_text(json.dumps({
        "task_id": source,
        "chat_id": "chat-ack-hook-002",
    }), encoding="utf-8")
    (sent / f"{event_id}.json").write_text(json.dumps({
        "event_id": event_id,
        "task_id": source,
        "message": "ordinary result",
    }), encoding="utf-8")

    mod.continuation_release_lease(event_id)
    assert not (data / "continuations").exists()
