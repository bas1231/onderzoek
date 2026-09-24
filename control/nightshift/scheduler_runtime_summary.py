#!/usr/bin/env python3
import subprocess, json
from pathlib import Path
ROOT=Path.home()/"prediction_research_prod"; U="prediction-research-hourly-director"
def val(a):
 p=subprocess.run(a,cwd=ROOT,text=True,capture_output=True,timeout=20)
 return (p.returncode,(p.stdout or p.stderr).strip().replace("\n"," | ")[:700])
pairs=[
 ("HEAD",["git","rev-parse","HEAD"]),("ORIGIN",["git","rev-parse","origin/main"]),
 ("TIMER_ENABLED",["systemctl","--user","is-enabled",U+".timer"]),
 ("TIMER_ACTIVE",["systemctl","--user","is-active",U+".timer"]),
 ("TIMER_STATE",["systemctl","--user","show",U+".timer","--property=LoadState,ActiveState,UnitFileState,LastTriggerUSec,NextElapseUSecRealtime"]),
 ("SERVICE_STATE",["systemctl","--user","show",U+".service","--property=LoadState,ActiveState,SubState,Result,ExecMainStatus"])
]
for k,a in pairs:
 rc,s=val(a); print(f"{k}=rc{rc}:{s}")
