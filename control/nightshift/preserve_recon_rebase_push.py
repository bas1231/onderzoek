#!/usr/bin/env python3
import subprocess,re
from pathlib import Path
R=Path.home()/"prediction_research_prod"; P="knowledge/recon/opportunity_graph.json"
def q(a,check=True):
 return subprocess.run(a,cwd=R,text=True,capture_output=True,timeout=120,check=check)
# verify target is dirty
if q(["git","diff","--quiet","--",P],check=False).returncode==0: raise SystemExit(31)
# fail closed on obvious secret material in the changed file
t=(R/P).read_text(errors="replace")
if re.search(r"(BEGIN [A-Z ]*PRIVATE KEY|api[_-]?key\s*[:=]|secret\s*[:=]|token\s*[:=])",t,re.I): raise SystemExit(32)
# preserve only this recon state
q(["git","add","--",P]); q(["git","commit","-m","preserve local recon opportunity graph before reconcile","--",P])
# remove only our diagnostic sync dirt
s=q(["git","status","--porcelain"],check=False).stdout.splitlines()
known=[x[3:] for x in s if x.strip() and not x.startswith("??") and x[3:].startswith("control/nightshift/")]
if known: q(["git","restore","--",*known])
# Any residual change remains protected; no rebase.
s=q(["git","status","--porcelain"],check=False).stdout.splitlines()
if any(x.strip() for x in s): raise SystemExit(33)
# lossless reconcile
r=q(["git","rebase","origin/main"],check=False)
if r.returncode:
 q(["git","rebase","--abort"],check=False); raise SystemExit(34)
# push only after clean successful rebase
r=q(["git","push","origin","HEAD:main"],check=False)
if r.returncode: raise SystemExit(35)
if q(["git","status","--porcelain"],check=False).stdout.strip(): raise SystemExit(36)
raise SystemExit(0)
