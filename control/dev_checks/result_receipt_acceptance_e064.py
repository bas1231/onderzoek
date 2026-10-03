from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_receipt_poller() -> None:
    poller = load(
        "receipt_poller_acceptance",
        ROOT / "control/bridge_commands/command_bus_poller.py",
    )
    event_id = "evt-20261003-e064"
    source_task_id = "DEV-PRED-RECEIPT-SOURCE-E064"
    receipt_id = f"RESULT-RECEIPT-{event_id}"
    receipt = {
        "schema": "PREDICTION_RESULT_RECEIPT_V1",
        "receipt_id": receipt_id,
        "event_id": event_id,
        "source_task_id": source_task_id,
        "created_at_utc": "2026-10-03T15:10:00Z",
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "issuer": {
            "model": "stdlib-acceptance",
            "reasoning_level": "deterministic",
        },
    }
    raw = json.dumps(receipt, sort_keys=True).encode("utf-8")
    path = f"control/bridge_commands/receipts/{receipt_id}.json"

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        bridge = root / "bridge"
        routes = bridge / "routes"
        inflight = bridge / "inflight"
        sent = bridge / "sent"
        state = root / "state"
        incidents = root / "incidents"
        for p in (routes, inflight, sent, state, incidents):
            p.mkdir(parents=True, exist_ok=True)

        old_values = {
            "BRIDGE_DATA": poller.BRIDGE_DATA,
            "ROUTES": poller.ROUTES,
            "TASK_STATE": poller.TASK_STATE,
            "INCIDENTS": poller.INCIDENTS,
            "remote_bytes": poller.remote_bytes,
            "dispatch_result_receipt": poller.dispatch_result_receipt,
        }
        calls = []
        try:
            poller.BRIDGE_DATA = bridge
            poller.ROUTES = routes
            poller.TASK_STATE = state
            poller.INCIDENTS = incidents
            poller.remote_bytes = lambda _path: raw
            poller.dispatch_result_receipt = (
                lambda obj, route, token: (
                    calls.append((obj["event_id"], route["chat_id"], route.get("consumer_id"), token))
                    or ("RESPONSE", 200, json.dumps({"ok": True, "event_id": obj["event_id"]}))
                )
            )

            (routes / f"{source_task_id}.json").write_text(
                json.dumps({
                    "version": 2,
                    "task_id": source_task_id,
                    "chat_id": "chat-e064",
                    "consumer_id": "tab-e064",
                }),
                encoding="utf-8",
            )
            (inflight / f"{event_id}.json").write_text(
                json.dumps({
                    "event_id": event_id,
                    "task_id": source_task_id,
                    "message": "NIGHTSHIFT_WSL_RESULT_V1 demo",
                }),
                encoding="utf-8",
            )

            assert poller.process_receipt(path, "a" * 40, "token-e064") == "RECEIPT_DISPATCHED"
            assert calls == [(event_id, "chat-e064", "tab-e064", "token-e064")]
            stored = json.loads((state / f"{receipt_id}.json").read_text(encoding="utf-8"))
            assert stored["status"] == "DISPATCHED"
            assert stored["event_id"] == event_id
            assert stored["source_task_id"] == source_task_id

            assert poller.process_receipt(path, "a" * 40, "token-e064") == "RECEIPT_ALREADY_CLAIMED"
            assert len(calls) == 1

            wrong_event_id = "evt-20261003-e064-wrong"
            wrong_receipt_id = f"RESULT-RECEIPT-{wrong_event_id}"
            wrong = dict(receipt)
            wrong["event_id"] = wrong_event_id
            wrong["receipt_id"] = wrong_receipt_id
            wrong["source_task_id"] = "DEV-PRED-WRONG-SOURCE-E064"
            wrong_raw = json.dumps(wrong, sort_keys=True).encode("utf-8")
            wrong_path = f"control/bridge_commands/receipts/{wrong_receipt_id}.json"
            (inflight / f"{wrong_event_id}.json").write_text(
                json.dumps({
                    "event_id": wrong_event_id,
                    "task_id": source_task_id,
                    "message": "wrong task guard",
                }),
                encoding="utf-8",
            )
            (routes / f"{wrong['source_task_id']}.json").write_text(
                json.dumps({
                    "version": 2,
                    "task_id": wrong["source_task_id"],
                    "chat_id": "chat-e064",
                    "consumer_id": "tab-e064",
                }),
                encoding="utf-8",
            )
            poller.remote_bytes = lambda _path: wrong_raw
            assert poller.process_receipt(wrong_path, "b" * 40, "token-e064") == "RECEIPT_REJECTED"
            assert len(calls) == 1
            rejected = json.loads((state / f"{wrong_receipt_id}.json").read_text(encoding="utf-8"))
            assert rejected["reason"] == "EVENT_TASK_MISMATCH"
        finally:
            for key, value in old_values.items():
                setattr(poller, key, value)


def test_continuation_delivery_metadata() -> None:
    cm = load(
        "continuation_receipt_acceptance",
        ROOT / "control/tampermonkey_multichat/continuation_manager.py",
    )
    with tempfile.TemporaryDirectory() as td:
        data = Path(td) / "bridge"
        routes = data / "routes"
        outbox = data / "outbox"
        routes.mkdir(parents=True)
        outbox.mkdir(parents=True)
        record = cm.start_external_continuation(
            data_dir=data,
            source_task_id="AUTOBUILD-E064",
            chat_id="chat-e064",
            expected_route_task_id="SESSION-ROUTE-E064",
            context_message="PREDICTION_AUTOBUILD_REQUEST_V1\ncandidate_id=E064",
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
        message = event["message"]
        assert f"delivery_event_id={event['event_id']}" in message
        assert f"delivery_task_id={event['task_id']}" in message
        assert "TRANSPORT RECEIPT:" in message
        assert "not a NEXT/DONE/BLOCKED outcome" in message


def main() -> int:
    test_receipt_poller()
    test_continuation_delivery_metadata()
    print("RESULT_RECEIPT_ACCEPTANCE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
