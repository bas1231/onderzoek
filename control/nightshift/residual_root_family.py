#!/usr/bin/env python3
import subprocess
from pathlib import Path
R=Path.home()/"prediction_research_prod"
p=subprocess.run(["git","status","--porcelain"],cwd=R,text=True,capture_output=True,timeout=30)
tracked=[x[3:] for x in p.stdout.splitlines() if x.strip() and not x.startswith("??") and not x[3:].startswith("control/nightshift/")]
if not tracked: raise SystemExit(230)
families=[("agents/",231),("knowledge/",232),("tests/",233),("docs/",234),("data/",235),("scripts/",236),("systemd/",237),(".github/",238)]
for pref,code in families:
 if any(x.startswith(pref) for x in tracked): raise SystemExit(code)
# top-level known project areas
if any("/" not in x for x in tracked): raise SystemExit(239)
raise SystemExit(240)
