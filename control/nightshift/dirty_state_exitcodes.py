#!/usr/bin/env python3
import subprocess
from pathlib import Path
R=Path.home()/"prediction_research_prod"
p=subprocess.run(["git","status","--porcelain"],cwd=R,text=True,capture_output=True,timeout=30)
if p.returncode: raise SystemExit(50)
lines=[x for x in p.stdout.splitlines() if x.strip()]
# classify conservatively
tracked=[x for x in lines if not x.startswith("??")]
untracked=[x for x in lines if x.startswith("??")]
if tracked: raise SystemExit(51)
if untracked: raise SystemExit(52)
raise SystemExit(0)
