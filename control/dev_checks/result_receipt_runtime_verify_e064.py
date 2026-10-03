from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOME = Path.home()
BUS_RUNTIME = HOME / ".local/share/prediction-command-bus/command_bus_poller.py"
WAKE_DIR = HOME / ".local/share/prediction-chat-bridge"
CM_RUNTIME = WAKE_DIR / "continuation_manager.py"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    assert BUS_RUNTIME.read_bytes() == (
        ROOT / "control/bridge_commands/command_bus_poller.py"
    ).read_bytes()
    assert CM_RUNTIME.read_bytes() == (
        ROOT / "control/tampermonkey_multichat/continuation_manager.py"
    ).read_bytes()

    bus = load("installed_result_receipt_poller_e064", BUS_RUNTIME)
    assert bus.RECEIPT_SCHEMA == "PREDICTION_RESULT_RECEIPT_V1"
    assert bus.RECEIPT_PREFIX == "control/bridge_commands/receipts/"
    assert callable(bus.process_receipt)
    assert callable(bus.dispatch_result_receipt)

    cm = load("installed_continuation_manager_e064", CM_RUNTIME)
    with tempfile.TemporaryDirectory() as td:
        data = Path(td) / "bridge"
        routes = data / "routes"
        outbox = data / "outbox"
        routes.mkdir(parents=True)
        outbox.mkdir(parents=True)
        record = cm.start_external_continuation(
            data_dir=data,
            source_task_id="AUTOBUILD-RUNTIME-E064",
            chat_id="chat-runtime-e064",
            expected_route_task_id="SESSION-ROUTE-RUNTIME-E064",
            context_message="PREDICTION_AUTOBUILD_REQUEST_V1\ncandidate_id=RUNTIME-E064",
            source_kind="AUTOBUILD",
        )
        assert cm.enqueue_attempt(
            record=record,
            data_dir=data,
            routes_dir=routes,
            outbox_dir=outbox,
            now=1000.0,
        )
        event = json.loads(next(outbox.glob("*.json")).read_text(encoding="utf-8"))
        assert f"delivery_event_id={event['event_id']}" in event["message"]
        assert f"delivery_task_id={event['task_id']}" in event["message"]

    current_event = "1791038786-c25e0ee643be"
    state = "missing"
    for folder in ("inflight", "sent"):
        p = WAKE_DIR / folder / f"{current_event}.json"
        if p.is_file():
            obj = json.loads(p.read_text(encoding="utf-8"))
            assert obj.get("event_id") == current_event
            assert obj.get("task_id") == "DEV-PRED-CONT-NEXT-4bc667283cb41c24f0294c35"
            state = folder
            break

    print("RESULT_RECEIPT_RUNTIME=PASS")
    print("POLLER_RUNTIME_MATCH=PASS")
    print("CONTINUATION_RUNTIME_MATCH=PASS")
    print("CURRENT_E061_EVENT_STATE=" + state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
