#!/usr/bin/env python3
import subprocess, json
from pathlib import Path
R=Path.home()/"prediction_research_prod"
p=subprocess.run(["python3","control/hourly/edge_hunter_cycle.py"],cwd=R,text=True,capture_output=True,timeout=240)
d={"schema":"HOURLY_FAILURE_V2","rc":p.returncode,"stdout_tail":(p.stdout or "")[-12000:],"stderr_tail":(p.stderr or "")[-12000:]}
path=R/"control/results/hourly_cycle_failure_latest.json"; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(d,indent=2),encoding="utf-8")
for a in (["git","add","control/results/hourly_cycle_failure_latest.json"],["git","commit","-m","diag: capture local hourly cycle failure"]):
 q=subprocess.run(a,cwd=R,text=True,capture_output=True,timeout=30)
 if q.returncode: raise SystemExit("git local failed rc="+str(q.returncode))
q=subprocess.run(["git","push","origin","HEAD:main"],cwd=R,text=True,capture_output=True,timeout=60)
if q.returncode: raise SystemExit("git push failed rc="+str(q.returncode))
raise SystemExit(0)
