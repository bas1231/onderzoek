from __future__ import annotations
from pathlib import Path
import hashlib, json

PROD=Path.home()/"prediction_research_prod"
CANON=Path.cwd()
STATUS=Path.home()/".local/state/prediction-research/prod-runtime-sync-latest.json"
FILES=[
"control/codex_supervisor/supervisor.py",
"control/codex_supervisor/candidate_dispatch.py",
"control/codex_supervisor/build_wake.py",
"control/tampermonkey_multichat/continuation_manager.py",
"knowledge/codex_runtime/CONFIG.json",
]

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def read_head() -> str:
    head_path=PROD/".git/HEAD"
    try:
        raw=head_path.read_text(encoding="utf-8").strip()
    except Exception as exc:
        return "UNREADABLE:"+type(exc).__name__
    if raw.startswith("ref: "):
        ref=raw[5:].strip()
        try:
            return (PROD/".git"/ref).read_text(encoding="utf-8").strip()
        except Exception:
            return "REF:"+ref
    return raw

def main() -> int:
    mismatch=[]
    for rel in FILES:
        c,p=CANON/rel,PROD/rel
        if not c.is_file() or not p.is_file():
            mismatch.append(rel+":MISSING")
        elif sha(c)!=sha(p):
            mismatch.append(rel)
    st={}
    try:
        st=json.loads(STATUS.read_text(encoding="utf-8"))
    except Exception as exc:
        st={"status":"UNREADABLE","error":type(exc).__name__}
    print("PROD_HEAD="+read_head(), flush=True)
    print("MISMATCH="+(",".join(mismatch) if mismatch else "NONE"), flush=True)
    print("SYNC_STATUS="+str(st.get("status")), flush=True)
    print("SYNC_HEAD="+str(st.get("head")), flush=True)
    print("SYNC_TIMESTAMP="+str(st.get("timestamp_utc")), flush=True)
    print("SYNC_ERROR="+str(st.get("error",""))[:700].replace("\n"," "), flush=True)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
