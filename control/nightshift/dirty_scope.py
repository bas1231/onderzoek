#!/usr/bin/env python3
import subprocess
from pathlib import Path
R=Path.home()/"prediction_research_prod"
p=subprocess.run(["git","status","--porcelain"],cwd=R,text=True,capture_output=True,timeout=30)
if p.returncode: raise SystemExit(100)
lines=[x for x in p.stdout.splitlines() if x.strip()]
tracked=[x for x in lines if not x.startswith("??")]
untracked=[x for x in lines if x.startswith("??")]
# 101 only tracked nightshift, 102 tracked elsewhere too, 103 only untracked, 104 clean
if tracked and all(x[3:].startswith("control/nightshift/") for x in tracked): raise SystemExit(101)
if tracked: raise SystemExit(102)
if untracked: raise SystemExit(103)
raise SystemExit(104)
