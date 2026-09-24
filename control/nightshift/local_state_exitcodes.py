#!/usr/bin/env python3
import subprocess, json
from pathlib import Path
R=Path.home()/"prediction_research_prod"
def run(a,t=30):
 p=subprocess.run(a,cwd=R,text=True,capture_output=True,timeout=t)
 return {"argv":a,"rc":p.returncode,"out":p.stdout[-6000:],"err":p.stderr[-6000:]}
d={"status":run(["git","status","--short","--branch"]),"log":run(["git","log","-5","--oneline"]),"head":run(["git","rev-parse","HEAD"]),"origin":run(["git","rev-parse","origin/main"]),"show":run(["git","show","HEAD:control/results/hourly_cycle_failure_latest.json"],30)}
Path("/tmp/e021.json").write_text(json.dumps(d))
# encode essential state into exit code only: 21 missing diag, 22 head!=origin, 23 dirty, 0 otherwise
if d["show"]["rc"]!=0: raise SystemExit(21)
if d["head"]["out"].strip()!=d["origin"]["out"].strip(): raise SystemExit(22)
if d["status"]["out"].strip().splitlines()[1:]: raise SystemExit(23)
raise SystemExit(0)
