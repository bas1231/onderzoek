from pathlib import Path
import importlib.util
import json
import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "continuation_manager_external_test",
    ROOT / "control/tampermonkey_multichat/continuation_manager.py",
)
c = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(c)


def test_external_continuation_is_idempotent_context_bound_and_routable(tmp_path):
    data = tmp_path / "bridge"
    routes = data / "routes"
    outbox = data / "outbox"
    task_state = tmp_path / "tasks"
    routes.mkdir(parents=True)
    outbox.mkdir(parents=True)
    task_state.mkdir(parents=True)

    record = c.start_external_continuation(
        data_dir=data,
        source_task_id="AUTOBUILD-abc123",
        chat_id="chat-1234",
        expected_route_task_id="SESSION-ROUTE-abc123",
        context_message="PREDICTION_AUTOBUILD_REQUEST_V1\ncandidate_id=CANARY",
        source_kind="AUTOBUILD",
    )
    again = c.start_external_continuation(
        data_dir=data,
        source_task_id="AUTOBUILD-abc123",
        chat_id="chat-1234",
        expected_route_task_id="SESSION-ROUTE-abc123",
        context_message="PREDICTION_AUTOBUILD_REQUEST_V1\ncandidate_id=CANARY",
        source_kind="AUTOBUILD",
    )
    assert again == record
    assert record["external_source_kind"] == "AUTOBUILD"
    assert record["expected_route_task_id"] == "SESSION-ROUTE-abc123"

    assert c.enqueue_attempt(
        record=record,
        data_dir=data,
        routes_dir=routes,
        outbox_dir=outbox,
        now=1000.0,
    )
    event = json.loads(next(outbox.glob("*.json")).read_text())
    assert "PREDICTION_AUTOBUILD_REQUEST_V1" in event["message"]
    assert "candidate_id=CANARY" in event["message"]
    assert "route_task_id=SESSION-ROUTE-abc123" in event["message"]

    with pytest.raises(ValueError, match="EXTERNAL_CONTINUATION_CONFLICT"):
        c.start_external_continuation(
            data_dir=data,
            source_task_id="AUTOBUILD-abc123",
            chat_id="chat-1234",
            expected_route_task_id="SESSION-ROUTE-abc123",
            context_message="different",
            source_kind="AUTOBUILD",
        )


def test_external_continuation_context_is_bounded(tmp_path):
    with pytest.raises(ValueError, match="EXTERNAL_CONTINUATION_CONTEXT"):
        c.start_external_continuation(
            data_dir=tmp_path,
            source_task_id="AUTOBUILD-x",
            chat_id="chat-1234",
            expected_route_task_id="SESSION-ROUTE-x",
            context_message="x" * 6001,
            source_kind="AUTOBUILD",
        )
