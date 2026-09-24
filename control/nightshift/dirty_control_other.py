#!/usr/bin/env python3
import subprocess
from pathlib import Path
R=Path.home()/"prediction_research_prod"
p=subprocess.run(["git","status","--porcelain"],cwd=R,text=True,capture_output=True,timeout=30)
paths=[x[3:] for x in p.stdout.splitlines() if x.strip() and not x.startswith("??") and x[3:].startswith("control/") and not x[3:].startswith(("control/nightshift/","control/hourly/","control/results/","control/jobs/","control/tasks/","control/recon/","control/runtime","control/bridge","control/agents/"))]
if not paths: raise SystemExit(130)
# classify top-level name deterministically by common prefixes
for pref,code in [("control/check",131),("control/state",132),("control/status",133),("control/scheduler",134),("control/receipts",135),("control/exchange",136),("control/contracts",137),("control/research",138)]:
    if any(x.startswith(pref) for x in paths): raise SystemExit(code)
raise SystemExit(139)
