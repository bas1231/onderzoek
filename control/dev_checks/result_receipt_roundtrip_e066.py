from __future__ import annotations
import json
import sys
import time
from pathlib import Path

if len(sys.argv) != 3:
    raise SystemExit("usage: result_receipt_roundtrip_e066.py <event_id> <source_task_id>")

event_id=sys.argv[1]
source_task_id=sys.argv[2]
receipt_id=f"RESULT-RECEIPT-{event_id}"
home=Path.home()
state=home/".local/state/prediction-command-bus/tasks"/f"{receipt_id}.json"
bridge=home/".local/share/prediction-chat-bridge"
sent=bridge/"sent"/f"{event_id}.json"
inflight=bridge/"inflight"/f"{event_id}.json"

deadline=time.time()+75
last={}
while time.time()<deadline:
    try:
        last=json.loads(state.read_text(encoding="utf-8")) if state.is_file() else {}
    except Exception:
        last={}
    sent_obj={}
    if sent.is_file():
        try:
            sent_obj=json.loads(sent.read_text(encoding="utf-8"))
        except Exception:
            sent_obj={}
    if (
        last.get("status")=="DISPATCHED"
        and last.get("event_id")==event_id
        and last.get("source_task_id")==source_task_id
        and sent_obj.get("event_id")==event_id
        and sent_obj.get("task_id")==source_task_id
        and not inflight.exists()
    ):
        print(
            "RESULT_RECEIPT_ROUNDTRIP=PASS"
            f"|event={event_id}|receipt_status=DISPATCHED|sent=true|inflight=false",
            flush=True,
        )
        raise SystemExit(0)
    time.sleep(2)

print(
    "RESULT_RECEIPT_ROUNDTRIP=FAIL"
    f"|event={event_id}|receipt_status={last.get('status','MISSING')}"
    f"|sent={sent.is_file()}|inflight={inflight.is_file()}",
    flush=True,
)
raise SystemExit(42)
