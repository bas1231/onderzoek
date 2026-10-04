from __future__ import annotations
import json, sys
from pathlib import Path

CID="CONT-1bd188daf0b712e863c2903f"
ROOT=Path.home()/".local/share/prediction-chat-bridge"

def load(p):
    try:
        x=json.loads(p.read_text(encoding="utf-8"))
        return x if isinstance(x,dict) else {}
    except Exception:
        return {}

def main():
    mode=(sys.argv[1] if len(sys.argv)>1 else "exists")
    p=ROOT/"continuations"/f"{CID}.json"
    if not p.is_file():
        return 11
    x=load(p)
    if x.get("continuation_id")!=CID or x.get("source_task_id")!="ASTRA-FULL-A2Z-REPAIR-20261005-V1":
        return 12
    if mode=="exists":
        return 0
    if mode=="attempted":
        return 0 if int(x.get("attempts") or 0)>=1 else 21
    if mode=="acked":
        return 0 if int(x.get("last_acked_attempt") or 0)>=1 else 22
    if mode=="terminal":
        return 0 if x.get("state") in {"NEXT_TASK_ACCEPTED","DONE","BLOCKED","CONFLICT","BLOCKED_TRANSPORT"} else 23
    return 2

if __name__=="__main__":
    raise SystemExit(main())
