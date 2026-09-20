from pathlib import Path
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


def write_result(results, task_id, status="completed"):
    result_dir = results / task_id
    result_dir.mkdir(parents=True, exist_ok=True)
    (result_dir / "RESULT.json").write_text(
        json.dumps({
            "task_id": task_id,
            "status": status,
            "task_class": "infrastructure",
            "hypothesis_id": "CONTROL-AUTO-CONTINUE",
            "exit_code": 0 if status == "completed" else 1,
            "source_commit": "abc123",
        }),
        encoding="utf-8",
    )


def base_state(task_id):
    return {
        "bridge_tasks": [task_id],
        "acked": [],
        "ai_acked": [],
    }


def test_ack_queues_and_ai_ack_consumes(tmp_path, monkeypatch):
    bb = load_bridge()
    state_file = tmp_path / "bridge_state.json"
    results = tmp_path / "results"
    task_id = "CONTROL-AUTO-CONTINUE-TEST-001"

    write_result(results, task_id)
    state_file.write_text(json.dumps(base_state(task_id)), encoding="utf-8")

    monkeypatch.setattr(bb, "STATE_FILE", state_file)
    monkeypatch.setattr(bb, "RESULTS", results)
    monkeypatch.setattr(bb, "lifecycle_update", lambda *args, **kwargs: None)

    ack = bb.acknowledge(task_id)
    assert ack["ok"] is True

    state = bb.load_state()
    assert state["control_continue_seen"] == [task_id]
    assert len(state["control_continue_queue"]) == 1

    offered = bb.next_ai_outbox_item()
    assert offered is not None
    assert offered["kind"] == "AI_WORK_BUNDLE"
    assert offered["schema"] == "PVA_CONTROL_CONTINUE_V1"
    assert offered["bundle"]["source_task_id"] == task_id
    assert offered["guardrails"]["direct_executor_route"] is False

    ai_ack = bb.acknowledge_ai(offered["task_id"])
    assert ai_ack["ok"] is True

    state = bb.load_state()
    assert offered["task_id"] in state["ai_acked"]

    # Other legitimate AI work (for example an hourly research wake)
    # may already be pending in the real incident directory. The invariant
    # under test is only that this control-continuation item is consumed.
    assert bb._next_control_continue_item(
        state,
        set(state.get("ai_acked", [])),
    ) is None


def test_malformed_queue_entry_is_skipped(tmp_path, monkeypatch):
    bb = load_bridge()
    state_file = tmp_path / "bridge_state.json"
    results = tmp_path / "results"
    task_id = "CONTROL-AUTO-CONTINUE-TEST-002"

    write_result(results, task_id)
    monkeypatch.setattr(bb, "RESULTS", results)
    item = bb._control_continue_item(task_id, "RESULT_ACKED")
    assert item is not None

    state = base_state(task_id)
    state["acked"] = [task_id]
    state["control_continue_seen"] = [task_id]
    state["control_continue_queue"] = [None, item]
    state_file.write_text(json.dumps(state), encoding="utf-8")

    monkeypatch.setattr(bb, "STATE_FILE", state_file)
    offered = bb.next_ai_outbox_item()
    assert offered["task_id"] == item["task_id"]
