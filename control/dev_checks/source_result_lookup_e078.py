from __future__ import annotations
import json
from pathlib import Path

TASK="DEV-PRED-CONT-NEXT-886a7af4b38ae890c31e2692"
ROOT=Path.home()/".local/share/prediction-chat-bridge"

def main():
    hits=[]
    for name in ("sent","inflight","outbox","continuation_abandoned"):
        d=ROOT/name
        if not d.is_dir():
            continue
        for p in d.glob("*.json"):
            try:
                obj=json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            if str(obj.get("task_id") or "") != TASK:
                continue
            msg=str(obj.get("message") or "").replace("\n"," ").replace("|","/")
            hits.append((name,p.name,msg))
    if not hits:
        print(f"SOURCE_RESULT|task={TASK}|found=0")
        return 42
    name,fn,msg=sorted(hits)[-1]
    print(f"SOURCE_RESULT|task={TASK}|found={len(hits)}|where={name}|event={fn}|message={msg[:500]}")
    return 42

if __name__=="__main__":
    raise SystemExit(main())
