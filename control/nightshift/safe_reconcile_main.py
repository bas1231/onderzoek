#!/usr/bin/env python3
import subprocess
from pathlib import Path
R=Path.home()/"prediction_research_prod"
def run(a,t=60):
 return subprocess.run(a,cwd=R,text=True,capture_output=True,timeout=t)
# Preserve local commits by rebasing; abort on any conflict. Never reset/drop.
p=run(["git","status","--porcelain"])
if p.returncode or p.stdout.strip(): raise SystemExit(41)
p=run(["git","rebase","origin/main"],120)
if p.returncode:
 run(["git","rebase","--abort"])
 raise SystemExit(42)
p=run(["git","push","origin","HEAD:main"],60)
if p.returncode: raise SystemExit(43)
p=run(["git","status","--porcelain"])
if p.returncode or p.stdout.strip(): raise SystemExit(44)
raise SystemExit(0)
