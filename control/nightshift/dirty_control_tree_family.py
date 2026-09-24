#!/usr/bin/env python3
import subprocess
from pathlib import Path
R=Path.home()/"prediction_research_prod"
p=subprocess.run(["git","status","--porcelain"],cwd=R,text=True,capture_output=True,timeout=30)
paths=[x[3:] for x in p.stdout.splitlines() if x.strip() and not x.startswith("??") and x[3:].startswith("control/") and not x[3:].startswith("control/nightshift/")]
groups=[("control/edge_hunter/",161),("control/lib/",162),("control/lifecycle/",163),("control/proofs/",164),("control/weather/",165),("control/builds/",166),("control/experiments/",167),("control/tampermonkey_multichat/",168),("control/browser_extension/",169)]
for pref,code in groups:
    if any(x.startswith(pref) for x in paths): raise SystemExit(code)
# remaining are top-level control files
raise SystemExit(170)
