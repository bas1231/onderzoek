from __future__ import annotations
import importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DATA=Path.home()/".local/share/prediction-chat-bridge"
CID="CONT-1bd188daf0b712e863c2903f"

def load_continuation():
    p=ROOT/"control"/"tampermonkey_multichat"/"continuation_manager.py"
    spec=importlib.util.spec_from_file_location("prediction_astra_full_a2z_kick",p)
    if spec is None or spec.loader is None:
        raise RuntimeError("continuation_manager unavailable")
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def main()->int:
    mod=load_continuation()
    p=DATA/"continuations"/f"{CID}.json"
    if not p.is_file():
        raise RuntimeError("ASTRA continuation missing")
    record=json.loads(p.read_text(encoding="utf-8"))
    queued=mod.enqueue_attempt(
        record=record,
        data_dir=DATA,
        routes_dir=DATA/"routes",
        outbox_dir=DATA/"outbox",
    )
    refreshed=json.loads(p.read_text(encoding="utf-8"))
    print(json.dumps({
        "status":"PASS",
        "continuation_id":CID,
        "queued_now":bool(queued),
        "state":refreshed.get("state"),
        "attempts":refreshed.get("attempts"),
        "last_event_id":refreshed.get("last_event_id"),
        "last_attempt_task_id":refreshed.get("last_attempt_task_id"),
        "expected_route_task_id":refreshed.get("expected_route_task_id"),
        "live_trading":False,
        "paid_actions":False,
        "wallet_actions":False
    },sort_keys=True))
    if int(refreshed.get("attempts") or 0) < 1:
        return 21
    return 0

if __name__=="__main__":
    raise SystemExit(main())
