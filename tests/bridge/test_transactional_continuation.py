from pathlib import Path
import json

from control.tampermonkey_multichat import continuation_manager as cm


def write_state(root: Path, task_id: str, status: str, *, auto_continue=False, claimed_at_utc=None):
    root.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "PREDICTION_COMMAND_BUS_TASK_STATE_V1",
        "task_id": task_id,
        "status": status,
        "auto_continue": auto_continue,
    }
    if claimed_at_utc is not None:
        payload["claimed_at_utc"] = claimed_at_utc
    (root / f"{task_id}.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def load_record(data_dir: Path, continuation_id: str):
    return json.loads(
        cm.continuation_path(data_dir, continuation_id).read_text(encoding="utf-8")
    )


def test_full_next_flow_retry_and_restart(tmp_path):
    data = tmp_path / "bridge"
    routes = data / "routes"
    outbox = data / "outbox"
    states = tmp_path / "task-state"
    source = "AUTO-CONTINUE-SOURCE-001"

    write_state(states, source, "DISPATCHED", auto_continue=True)
    record = cm.start_for_result_ack(
        data_dir=data,
        task_state_dir=states,
        source_task_id=source,
        chat_id="chat-continuation-test-001",
    )
    assert record is not None
    cid = record["continuation_id"]
    assert record["state"] == "CONTINUE_REQUESTED"
    assert record["expected_next_task_id"].startswith("DEV-PRED-CONT-NEXT-")
    assert record["expected_route_task_id"] == source

    cm.maintain_for_chat(
        data_dir=data,
        task_state_dir=states,
        routes_dir=routes,
        outbox_dir=outbox,
        chat_id="chat-continuation-test-001",
        now=1000.0,
    )
    record = load_record(data, cid)
    assert record["state"] == "CONTINUE_SENT"
    assert record["attempts"] == 1
    first_events = sorted(outbox.glob("*.json"))
    assert len(first_events) == 1
    first = json.loads(first_events[0].read_text(encoding="utf-8"))
    assert first["continuation_id"] == cid
    assert first["task_id"].endswith("-A01")
    assert f"continuation_id={cid}" in first["message"]

    # Before the retry deadline there is no second delivery.
    cm.maintain_for_chat(
        data_dir=data,
        task_state_dir=states,
        routes_dir=routes,
        outbox_dir=outbox,
        chat_id="chat-continuation-test-001",
        now=1119.0,
    )
    assert len(list(outbox.glob("*.json"))) == 1

    # After the deadline a new delivery ID/task ID is used but the same
    # logical continuation and expected child IDs remain.
    cm.maintain_for_chat(
        data_dir=data,
        task_state_dir=states,
        routes_dir=routes,
        outbox_dir=outbox,
        chat_id="chat-continuation-test-001",
        now=1121.0,
    )
    record = load_record(data, cid)
    assert record["attempts"] == 2
    events = sorted(outbox.glob("*.json"))
    assert len(events) == 2
    second = json.loads(events[1].read_text(encoding="utf-8"))
    assert second["continuation_id"] == cid
    assert second["task_id"].endswith("-A02")
    assert second["task_id"] != first["task_id"]

    child = record["expected_next_task_id"]
    write_state(states, child, "CLAIMED")
    cm.maintain_for_chat(
        data_dir=data,
        task_state_dir=states,
        routes_dir=routes,
        outbox_dir=outbox,
        chat_id="chat-continuation-test-001",
        now=1400.0,
    )
    record = load_record(data, cid)
    assert record["state"] == "NEXT_TASK_CREATED"
    assert len(list(outbox.glob("*.json"))) == 2

    write_state(states, child, "DISPATCHED")
    cm.maintain_for_chat(
        data_dir=data,
        task_state_dir=states,
        routes_dir=routes,
        outbox_dir=outbox,
        chat_id="chat-continuation-test-001",
        now=1600.0,
    )
    record = load_record(data, cid)
    assert record["state"] == "NEXT_TASK_ACCEPTED"

    # Simulated restart: persisted terminal state cannot reoffer.
    cm.maintain_for_chat(
        data_dir=data,
        task_state_dir=states,
        routes_dir=routes,
        outbox_dir=outbox,
        chat_id="chat-continuation-test-001",
        now=9999.0,
    )
    assert len(list(outbox.glob("*.json"))) == 2


def test_done_and_blocked_are_durable_command_bus_outcomes(tmp_path):
    data = tmp_path / "bridge"
    states = tmp_path / "task-state"
    routes = data / "routes"
    outbox = data / "outbox"
    source = "AUTO-CONTINUE-SOURCE-002"
    write_state(states, source, "DISPATCHED", auto_continue=True)

    record = cm.start_for_result_ack(
        data_dir=data,
        task_state_dir=states,
        source_task_id=source,
        chat_id="chat-continuation-test-002",
    )
    assert record is not None
    write_state(states, record["expected_done_task_id"], "CLAIMED")
    assert cm.reconcile(record, states) is True
    assert record["state"] == "DONE_RECEIPT_CREATED"
    write_state(states, record["expected_done_task_id"], "DISPATCHED")
    assert cm.reconcile(record, states) is True
    assert record["state"] == "DONE"

    # Terminal outcome is never reoffered.
    cm._atomic_json(cm.continuation_path(data, record["continuation_id"]), record)
    cm.maintain_for_chat(
        data_dir=data,
        task_state_dir=states,
        routes_dir=routes,
        outbox_dir=outbox,
        chat_id="chat-continuation-test-002",
        now=5000.0,
    )
    assert list(outbox.glob("*.json")) == []


def test_mutually_exclusive_outcomes_fail_closed(tmp_path):
    data = tmp_path / "bridge"
    states = tmp_path / "task-state"
    source = "AUTO-CONTINUE-SOURCE-003"
    write_state(states, source, "DISPATCHED", auto_continue=True)
    record = cm.start_for_result_ack(
        data_dir=data,
        task_state_dir=states,
        source_task_id=source,
        chat_id="chat-continuation-test-003",
    )
    assert record is not None

    write_state(states, record["expected_next_task_id"], "CLAIMED")
    write_state(states, record["expected_done_task_id"], "CLAIMED")
    assert cm.reconcile(record, states) is True
    assert record["state"] == "CONFLICT"


def test_full_source_id_hash_prevents_truncation_collision():
    common = "X" * 140
    first = cm.ids_for(common + "-A")
    second = cm.ids_for(common + "-B")
    assert first["continuation_id"] != second["continuation_id"]
    assert first["expected_next_task_id"] != second["expected_next_task_id"]


def test_auto_continue_is_explicit_opt_in(tmp_path):
    data = tmp_path / "bridge"
    states = tmp_path / "task-state"
    source = "NORMAL-TASK-NO-AUTO"
    write_state(states, source, "DISPATCHED", auto_continue=False)
    assert cm.start_for_result_ack(
        data_dir=data,
        task_state_dir=states,
        source_task_id=source,
        chat_id="chat-continuation-test-004",
    ) is None
    assert not cm.continuation_dir(data).exists()


def test_bounded_attempts_end_blocked_transport(tmp_path):
    data = tmp_path / "bridge"
    states = tmp_path / "task-state"
    routes = data / "routes"
    outbox = data / "outbox"
    source = "AUTO-CONTINUE-SOURCE-005"
    write_state(states, source, "DISPATCHED", auto_continue=True)
    record = cm.start_for_result_ack(
        data_dir=data,
        task_state_dir=states,
        source_task_id=source,
        chat_id="chat-continuation-test-005",
    )
    assert record is not None

    for n in range(cm.MAX_ATTEMPTS):
        assert cm.enqueue_attempt(
            record=record,
            data_dir=data,
            routes_dir=routes,
            outbox_dir=outbox,
            now=1000.0 + n * (cm.RETRY_AFTER_SECONDS + 1),
        ) is True

    assert cm.enqueue_attempt(
        record=record,
        data_dir=data,
        routes_dir=routes,
        outbox_dir=outbox,
        now=1000.0 + cm.MAX_ATTEMPTS * (cm.RETRY_AFTER_SECONDS + 1),
    ) is False
    record = load_record(data, record["continuation_id"])
    assert record["state"] == "BLOCKED_TRANSPORT"
    assert len(list(outbox.glob("*.json"))) == cm.MAX_ATTEMPTS


def test_stale_claim_fails_closed_instead_of_stalling(tmp_path):
    data = tmp_path / "bridge"
    states = tmp_path / "task-state"
    source = "AUTO-CONTINUE-SOURCE-STALE"
    write_state(states, source, "DISPATCHED", auto_continue=True)
    record = cm.start_for_result_ack(
        data_dir=data,
        task_state_dir=states,
        source_task_id=source,
        chat_id="chat-continuation-stale",
    )
    assert record is not None

    write_state(
        states,
        record["expected_next_task_id"],
        "CLAIMED",
        claimed_at_utc="2026-10-02T10:00:00Z",
    )
    assert cm.reconcile(
        record,
        states,
        now=1790935801.0,
    ) is True
    assert record["state"] == "BLOCKED"
    assert "CLAIMED" in record["history"][-1]["detail"]
