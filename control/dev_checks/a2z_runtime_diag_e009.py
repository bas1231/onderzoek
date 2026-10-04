from __future__ import annotations
import json, subprocess
from pathlib import Path

ROOT=Path.home()/"prediction_research_prod"

def run(*argv):
    p=subprocess.run(list(argv),cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=20)
    return p.returncode,(p.stdout or "").strip()

def j(path):
    try:
        x=json.loads(path.read_text(encoding="utf-8"))
        return x if isinstance(x,dict) else {}
    except Exception:
        return {}

def clean(s,n=500):
    return " ".join(str(s).replace("|","/").split())[:n]

def main():
    _, sup=run("systemctl","--user","show","prediction-codex-supervisor.service",
              "--property=ActiveState,SubState,Result,ExecMainStatus,ExecMainCode")
    _, hour=run("systemctl","--user","show","prediction-research-hourly-director.service",
               "--property=ActiveState,SubState,Result,ExecMainStatus,ExecMainCode")
    _, log=run("journalctl","--user","-u","prediction-codex-supervisor.service","-n","80","--no-pager")
    lines=[x.strip() for x in log.splitlines() if x.strip()]
    interesting=[x for x in lines if any(k in x.lower() for k in (
        "error","failed","blocked","invalid","usage","quota","traceback","exception","revision","stale","pin","model"
    ))]
    last=interesting[-1] if interesting else (lines[-1] if lines else "NO_JOURNAL")
    st=j(ROOT/"knowledge/codex_runtime/STATE.json")
    bl=j(ROOT/"knowledge/codex_runtime/BLOCKER.json")
    runs=[]
    for p in (ROOT/"knowledge/runs").glob("hourly-*.json"):
        try:
            x=j(p)
            if x.get("run_id")==p.stem:
                runs.append((p.stat().st_mtime,p.name,x.get("status"),x.get("recon_scout",{}).get("economic_conclusion"),x.get("agent_control_plane",{}).get("queue_count")))
        except Exception:
            pass
    latest=max(runs) if runs else None
    print("A2Z_DIAG"
          +"|supervisor="+clean(sup,260)
          +"|hourly="+clean(hour,260)
          +"|codex_state="+clean(st,280)
          +"|blocker="+clean(bl,220)
          +"|latest_run="+clean(latest,320)
          +"|journal="+clean(last,900))
    return 42

if __name__=="__main__":
    raise SystemExit(main())
