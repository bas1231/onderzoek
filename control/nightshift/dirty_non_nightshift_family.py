#!/usr/bin/env python3
import subprocess
from pathlib import Path
R=Path.home()/"prediction_research_prod"
p=subprocess.run(["git","status","--porcelain"],cwd=R,text=True,capture_output=True,timeout=30)
paths=[x[3:] for x in p.stdout.splitlines() if x.strip() and not x.startswith("??") and not x[3:].startswith("control/nightshift/")]
if not paths: raise SystemExit(110)
families=[("control/hourly/",111),("control/results/",112),("control/",113),("reports/",114),("nightwork-reports/",115),("agents/",116),("knowledge/",117),("tests/",118)]
for pref,code in families:
    if any(x.startswith(pref) for x in paths): raise SystemExit(code)
raise SystemExit(119)
