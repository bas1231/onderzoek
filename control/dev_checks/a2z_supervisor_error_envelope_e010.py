from __future__ import annotations
import json, subprocess
from pathlib import Path

ROOT=Path.home()/"prediction_research_prod"

def run(argv):
    p=subprocess.run(argv,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=25)
    return p.returncode,(p.stdout or "").strip()

def load(path):
    try:
        x=json.loads(path.read_text(encoding="utf-8"))
        return x if isinstance(x,dict) else {}
    except Exception:
        return {}

def flat(x,n):
    return " ".join(str(x).replace("|","/").split())[:n]

def main():
    _,sup=run(["systemctl","--user","show","prediction-codex-supervisor.service",
               "--property=ActiveState,SubState,Result,ExecMainStatus,ExecMainCode"])
    _,hour=run(["systemctl","--user","show","prediction-research-hourly-director.service",
                "--property=ActiveState,SubState,Result,ExecMainStatus,ExecMainCode"])
    _,log=run(["journalctl","--user","-u","prediction-codex-supervisor.service","-n","120","--no-pager"])
    lines=[x.strip() for x in log.splitlines() if x.strip()]
    keys=("error","failed","blocked","invalid","usage","quota","traceback","exception","model","pin","revision","http 400","400")
    interesting=[x for x in lines if any(k in x.lower() for k in keys)]
    journal=" || ".join(interesting[-4:] if interesting else lines[-4:])
    state=load(ROOT/"knowledge/codex_runtime/STATE.json")
    blocker=load(ROOT/"knowledge/codex_runtime/BLOCKER.json")
    detail=("A2Z_DIAG "
            +"supervisor="+flat(sup,260)
            +" ; hourly="+flat(hour,260)
            +" ; codex_state="+flat(state,320)
            +" ; blocker="+flat(blocker,320)
            +" ; journal="+flat(journal,1800))
    print("ERROR_CLASS=TaskError")
    print("ERROR="+detail)
    return 2

if __name__=="__main__":
    raise SystemExit(main())
