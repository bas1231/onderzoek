#!/usr/bin/env python3
import subprocess, json
from pathlib import Path
R=Path.home()/"prediction_research_prod"
p=subprocess.run(["python3","control/hourly/edge_hunter_cycle.py"],cwd=R,text=True,capture_output=True,timeout=240)
payload={"schema":"HOURLY_FAILURE_V1","rc":p.returncode,"stdout_tail":(p.stdout or "")[-12000:],"stderr_tail":(p.stderr or "")[-12000:]}
path=R/"control/results/hourly_cycle_failure_latest.json"
path.parent.mkdir(parents=True,exist_ok=True)
path.write_text(json.dumps(payload,indent=2),encoding="utf-8")
subprocess.run(["git","add",str(path.relative_to(R))],cwd=R,check=True)
subprocess.run(["git","commit","-m","diag: capture local hourly cycle failure"],cwd=R,check=False)
subprocess.run(["git","push","origin","HEAD:main"],cwd=R,check=False)
print("CAPTURED_RC="+str(p.returncode))
raise SystemExit(0)
