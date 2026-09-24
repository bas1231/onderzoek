#!/usr/bin/env python3
import subprocess
from pathlib import Path
R=Path.home()/"prediction_research_prod"
p=subprocess.run(["git","status","--porcelain"],cwd=R,text=True,capture_output=True,timeout=30)
ps=[x[3:] for x in p.stdout.splitlines() if x.strip() and not x.startswith("??") and not x[3:].startswith(("control/nightshift/","knowledge/","control/","agents/","tests/","reports/","nightwork-reports/"))]
if not ps: raise SystemExit(50)
x=ps[0]
for pref,code in [("README",51),("pyproject",52),("requirements",53),("config",54),("data/",55),("scripts/",56),("systemd/",57),(".github/",58),("docs/",59)]:
 if x.startswith(pref): raise SystemExit(code)
raise SystemExit(60)
