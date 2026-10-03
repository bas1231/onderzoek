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


def setup_paths(mod, tmp_path, monkeypatch):
    base = mod.base
    data = tmp_path / "bridge"
    routes = data / "routes"
    outbox = data / "outbox"
    inflight = data / "inflight"
    sent = data / "sent"
    states = tmp_path / "task-state"
    for path in (routes, outbox, inflight, sent, states):
        path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(base, "DATA_DIR", data)
    monkeypatch.setattr(base, "ROUTES", routes)
    monkeypatch.setattr(base, "OUTBOX", outbox)
    monkeypatch.setattr(base, "INFLIGHT", inflight)
    monkeypatch.setattr(base, "SENT", sent)
    monkeypatch.setattr(mod, "TASK_STATE_DIR", states)
    return base, data, routes, outbox, sent, states


def write_source_state(states, task_id, auto_continue):
    (states / f"{task_id}.json").write_text(json.dumps({
        "schema": "PREDICTION_COMMAND_BUS_TASK_STATE_V1",
        "task_id": task_id,
        "status": "DISPATCHED",
        "auto_continue": auto_continue,
    }), encoding="utf-8")


def test_ack_hook_creates_exactly_one_continuation(tmp_path, monkeypatch):
    mod = load_overlay()
    _, data, _, _, _, states = setup_paths(mod, tmp_path, monkeypatch)

    source = "ACK-HOOK-SOURCE-001"
    event = {
        "event_id": "event-ack-hook-001",
        "task_id": source,
        "message": "NIGHTSHIFT_WSL_RESULT_V1 task=ACK-HOOK-SOURCE-001 status=PASS exit=0",
    }
    write_source_state(states, source, True)

    mod.continuation_ack_hook(
        event,
        chat_id="chat-ack-hook-001",
        consumer_id="tab-ack-hook-001",
        already_acked=False,
    )
    records = list((data / "continuations").glob("CONT-*.json"))
    assert len(records) == 1
    first = json.loads(records[0].read_text(encoding="utf-8"))
    assert first["source_task_id"] == source
    assert first["chat_id"] == "chat-ack-hook-001"
    assert first["state"] == "CONTINUE_REQUESTED"

    # Duplicate /ack is idempotent.
    mod.continuation_ack_hook(
        event,
        chat_id="chat-ack-hook-001",
        consumer_id="tab-ack-hook-001",
        already_acked=True,
    )
    records2 = list((data / "continuations").glob("CONT-*.json"))
    assert len(records2) == 1
    second = json.loads(records2[0].read_text(encoding="utf-8"))
    assert second["continuation_id"] == first["continuation_id"]

    if hasattr(mod.base, "ACK_HOOK"):
        assert mod.base.ACK_HOOK is mod.continuation_ack_hook


def test_ack_hook_ignores_normal_tasks(tmp_path, monkeypatch):
    mod = load_overlay()
    _, data, _, _, _, states = setup_paths(mod, tmp_path, monkeypatch)

    source = "ACK-HOOK-NORMAL-001"
    write_source_state(states, source, False)
    mod.continuation_ack_hook(
        {"event_id": "normal-event", "task_id": source, "message": "ordinary result"},
        chat_id="chat-ack-hook-002",
        consumer_id="tab-ack-hook-002",
        already_acked=False,
    )
    assert not (data / "continuations").exists()


def test_continuation_delivery_ack_is_nonterminal_transport_evidence(tmp_path, monkeypatch):
    mod = load_overlay()
    _, data, routes, outbox, _, states = setup_paths(mod, tmp_path, monkeypatch)

    source = "ACK-HOOK-CONTINUATION-001"
    write_source_state(states, source, True)
    record = mod.continuation.start_for_result_ack(
        data_dir=data,
        task_state_dir=states,
        source_task_id=source,
        chat_id="chat-ack-hook-003",
    )
    assert record is not None

    mod.continuation.maintain_for_chat(
        data_dir=data,
        task_state_dir=states,
        routes_dir=routes,
        outbox_dir=outbox,
        chat_id="chat-ack-hook-003",
        now=1000.0,
    )
    record = json.loads(
        mod.continuation.continuation_path(data, record["continuation_id"]).read_text(encoding="utf-8")
    )
    assert record["state"] == "CONTINUE_QUEUED"
    assert record["attempts"] == 1

    event_path = outbox / f"{record['last_event_id']}.json"
    event = json.loads(event_path.read_text(encoding="utf-8"))
    event_path.unlink()

    mod.continuation_ack_hook(
        event,
        chat_id="chat-ack-hook-003",
        consumer_id="tab-ack-hook-003",
        already_acked=False,
    )
    after = json.loads(
        mod.continuation.continuation_path(data, record["continuation_id"]).read_text(encoding="utf-8")
    )
    assert after["state"] == "CONTINUE_SENT"
    assert after["attempts"] == 1
    assert after["last_acked_attempt"] == 1

    # A duplicate browser ACK must not consume the continuation or add attempts.
    mod.continuation_ack_hook(
        event,
        chat_id="chat-ack-hook-003",
        consumer_id="tab-ack-hook-003",
        already_acked=True,
    )
    duplicate = json.loads(
        mod.continuation.continuation_path(data, record["continuation_id"]).read_text(encoding="utf-8")
    )
    assert duplicate["state"] == "CONTINUE_SENT"
    assert duplicate["attempts"] == 1
    assert duplicate["last_acked_attempt"] == 1


def test_compatibility_release_hook_uses_sent_event_and_propagates_failures(tmp_path, monkeypatch):
    mod = load_overlay()
    base, _, routes, _, sent, states = setup_paths(mod, tmp_path, monkeypatch)

    source = "ACK-HOOK-COMPAT-001"
    event_id = "compat-event-001"
    write_source_state(states, source, True)
    (routes / f"{source}.json").write_text(json.dumps({
        "version": 2,
        "task_id": source,
        "chat_id": "chat-ack-hook-004",
        "consumer_id": None,
    }), encoding="utf-8")
    (sent / f"{event_id}.json").write_text(json.dumps({
        "event_id": event_id,
        "task_id": source,
        "message": "compat result",
    }), encoding="utf-8")

    # The compatibility function is retained even on fresh runtimes so the
    # installed inflight-patched base can compose without being overwritten.
    mod.continuation_release_lease(event_id)
    records = list((base.DATA_DIR / "continuations").glob("CONT-*.json"))
    assert len(records) == 1
    record = json.loads(records[0].read_text(encoding="utf-8"))
    assert record["chat_id"] == "chat-ack-hook-004"


def test_stale_unacked_auto_continue_result_arms_recovery_heartbeat(tmp_path, monkeypatch):
    mod = load_overlay()
    base, data, routes, outbox, _, states = setup_paths(mod, tmp_path, monkeypatch)

    source = "ACK-HEARTBEAT-SOURCE-001"
    chat = "chat-ack-heartbeat-001"
    write_source_state(states, source, True)
    (routes / f"{source}.json").write_text(json.dumps({
        "version": 2,
        "task_id": source,
        "chat_id": chat,
        "consumer_id": None,
    }), encoding="utf-8")

    event_id = "stale-unacked-result-001"
    inflight = base.INFLIGHT / f"{event_id}.json"
    inflight.write_text(json.dumps({
        "event_id": event_id,
        "task_id": source,
        "message": "NIGHTSHIFT_WSL_RESULT_V1 task=ACK-HEARTBEAT-SOURCE-001 status=PASS exit=0",
        "created_at": 1000.0,
        "source": "wsl_result",
    }), encoding="utf-8")

    recovered = mod.recover_unacked_result_heartbeat(
        chat,
        now=1000.0 + mod.UNACKED_RESULT_HEARTBEAT_SECONDS + 1,
    )
    assert recovered == 1
    assert inflight.is_file()

    cid = mod.continuation.ids_for(source)["continuation_id"]
    record = json.loads(
        mod.continuation.continuation_path(data, cid).read_text(encoding="utf-8")
    )
    assert record["state"] == "CONTINUE_REQUESTED"
    assert record["recovery_reason"] == "RESULT_ACK_TIMEOUT"
    assert "INFLIGHT" in record["history"][0]["detail"]

    mod.continuation.maintain_for_chat(
        data_dir=data,
        task_state_dir=states,
        routes_dir=routes,
        outbox_dir=outbox,
        chat_id=chat,
        now=2000.0,
    )
    record = json.loads(
        mod.continuation.continuation_path(data, cid).read_text(encoding="utf-8")
    )
    assert record["state"] == "CONTINUE_QUEUED"
    assert record["attempts"] == 1
    wake = json.loads((outbox / f"{record['last_event_id']}.json").read_text(encoding="utf-8"))
    assert wake["source"] == "control_continuation_v2"
    assert "recovery_reason=RESULT_ACK_TIMEOUT" in wake["message"]
    assert inflight.is_file()


def test_unacked_result_heartbeat_is_bounded_to_stale_auto_continue_same_chat(tmp_path, monkeypatch):
    mod = load_overlay()
    base, data, routes, _, _, states = setup_paths(mod, tmp_path, monkeypatch)

    chat = "chat-ack-heartbeat-guard"
    other_chat = "chat-ack-heartbeat-other"

    cases = [
        ("FRESH-AUTO", True, chat, 1000.0 + mod.UNACKED_RESULT_HEARTBEAT_SECONDS - 1),
        ("ORDINARY-NO-AUTO", False, chat, 1000.0 + mod.UNACKED_RESULT_HEARTBEAT_SECONDS + 1),
        ("OTHER-CHAT-AUTO", True, other_chat, 1000.0 + mod.UNACKED_RESULT_HEARTBEAT_SECONDS + 1),
    ]

    for source, auto, route_chat, now in cases:
        write_source_state(states, source, auto)
        (routes / f"{source}.json").write_text(json.dumps({
            "version": 2,
            "task_id": source,
            "chat_id": route_chat,
            "consumer_id": None,
        }), encoding="utf-8")
        event_id = f"event-{source.lower()}"
        (base.INFLIGHT / f"{event_id}.json").write_text(json.dumps({
            "event_id": event_id,
            "task_id": source,
            "message": "result",
            "created_at": 1000.0,
            "source": "wsl_result",
        }), encoding="utf-8")
        assert mod.recover_unacked_result_heartbeat(chat, now=now) == 0
        cid = mod.continuation.ids_for(source)["continuation_id"]
        assert not mod.continuation.continuation_path(data, cid).exists()
        event_path = base.INFLIGHT / f"{event_id}.json"
        assert event_path.is_file()
        event_path.unlink()
        (routes / f"{source}.json").unlink()
        (states / f"{source}.json").unlink()
