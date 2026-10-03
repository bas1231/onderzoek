from __future__ import annotations
from pathlib import Path
import hashlib, json, subprocess

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
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*a):
    return subprocess.run(["git","-C",str(PROD),*a],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=False,timeout=20)
def main():
    head=git("rev-parse","HEAD").stdout.strip()
    branch=git("branch","--show-current").stdout.strip()
    dirty=git("status","--porcelain=v1").stdout.splitlines()
    mismatch=[]
    for rel in FILES:
        c,p=CANON/rel,PROD/rel
        if not c.is_file() or not p.is_file(): mismatch.append(rel+":MISSING")
        elif sha(c)!=sha(p): mismatch.append(rel)
    st={}
    try: st=json.loads(STATUS.read_text())
    except Exception: pass
    print("PROD_HEAD="+head)
    print("PROD_BRANCH="+branch)
    print("PROD_DIRTY_COUNT="+str(len(dirty)))
    print("MISMATCH="+(",".join(mismatch) if mismatch else "NONE"))
    print("SYNC_STATUS="+str(st.get("status")))
    print("SYNC_HEAD="+str(st.get("head")))
    print("SYNC_ERROR="+str(st.get("error",""))[:500].replace("\n"," "))
    return 0
if __name__=="__main__": raise SystemExit(main())
