#!/usr/bin/env python3
import subprocess
from pathlib import Path
R=Path.home()/"prediction_research_prod"
p=subprocess.run(["git","status","--porcelain"],cwd=R,text=True,capture_output=True,timeout=30)
paths=[x[3:] for x in p.stdout.splitlines() if x.strip() and not x.startswith("??") and x[3:].startswith("control/") and not x[3:].startswith(("control/nightshift/","control/hourly/","control/results/"))]
if not paths: raise SystemExit(120)
families=[("control/jobs/",121),("control/tasks/",122),("control/recon/",123),("control/runtime",124),("control/bridge",125),("control/agents/",126)]
for pref,code in families:
    if any(x.startswith(pref) for x in paths): raise SystemExit(code)
raise SystemExit(129)
