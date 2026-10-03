from __future__ import annotations
import json
import time
from pathlib import Path

HOME=Path.home()
STATE=HOME/".local/state/prediction-command-bus/tasks"
BRIDGE=HOME/".local/share/prediction-chat-bridge"
CASES=[
 ("1791038939-b367ffe27312","DEV-PRED-PROD-DIVERGENCE-COMMITS-20261003-E062"),
 ("1791038937-3ce66aaea326","DEV-PRED-PROD-DIVERGENCE-PATHS-20261003-E063"),
 ("1791040645-dadea09abec1","DEV-PRED-RESULT-RECEIPT-INSTALL-20261003-E064"),
]

def load(p:Path):
    try:
        obj=json.loads(p.read_text(encoding="utf-8"))
        return obj if isinstance(obj,dict) else {}
    except Exception:
        return {}

deadline=time.time()+45
last=[]
while time.time()<deadline:
    ok=True
    rows=[]
    for event,source in CASES:
        rid=f"RESULT-RECEIPT-{event}"
        st=load(STATE/f"{rid}.json")
        status=str(st.get("status") or "MISSING")
        sent=(BRIDGE/"sent"/f"{event}.json").is_file()
        inflight=(BRIDGE/"inflight"/f"{event}.json").is_file()
        rows.append((event,source,status,sent,inflight))
        if status!="DISPATCHED" or not sent:
            ok=False
    last=rows
    if ok:
        print("RESULT_RECEIPT_LIVE_CANARY=PASS|cases=3|dispatched=3|sent=3",flush=True)
        raise SystemExit(0)
    time.sleep(2)

detail=";".join(
    f"{event}:{status}:sent={sent}:inflight={inflight}"
    for event,_source,status,sent,inflight in last
)
print("RESULT_RECEIPT_LIVE_CANARY=FAIL|"+detail,flush=True)
raise SystemExit(42)
