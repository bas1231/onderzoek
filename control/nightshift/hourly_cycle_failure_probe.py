#!/usr/bin/env python3
import subprocess
from pathlib import Path
R=Path.home()/"prediction_research_prod"
p=subprocess.run(["python3","control/hourly/edge_hunter_cycle.py"],cwd=R,text=True,capture_output=True,timeout=240)
err=(p.stderr or "").strip().replace("\n"," | ")
out=(p.stdout or "").strip().replace("\n"," | ")
print("CYCLE_RC="+str(p.returncode))
print("STDERR_TAIL="+err[-5000:])
print("STDOUT_TAIL="+out[-3000:])
raise SystemExit(0)
