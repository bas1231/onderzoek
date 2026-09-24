#!/usr/bin/env python3
import json, subprocess
from pathlib import Path

ROOT=Path.home()/"prediction_research_prod"
UNIT="prediction-research-hourly-director"
def run(argv):
    p=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True,timeout=20)
    return {"argv":argv,"rc":p.returncode,"out":p.stdout.strip()[-2500:],"err":p.stderr.strip()[-1200:]}

checks=[
 ["git","status","--short","--branch"],
 ["git","rev-parse","HEAD"],
 ["git","rev-parse","origin/main"],
 ["systemctl","--user","is-enabled",UNIT+".timer"],
 ["systemctl","--user","is-active",UNIT+".timer"],
 ["systemctl","--user","show",UNIT+".timer","--property=LoadState,ActiveState,UnitFileState,LastTriggerUSec,NextElapseUSecRealtime"],
 ["systemctl","--user","show",UNIT+".service","--property=LoadState,ActiveState,SubState,Result,ExecMainStatus"],
 ["systemctl","--user","list-timers",UNIT+".timer","--no-pager"],
]
print(json.dumps({"schema":"SCHED_RUNTIME_DIAG_V1","checks":[run(x) for x in checks]},separators=(",",":")))
