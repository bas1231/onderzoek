#!/usr/bin/env python3
import subprocess
from pathlib import Path
R=Path.home()/"prediction_research_prod"
P="control/tampermonkey_multichat/prediction-chat-wake.user.js"
def q(a,check=True):
 return subprocess.run(a,cwd=R,text=True,capture_output=True,timeout=60,check=check)
# Preserve only the known local working edit in a local commit.
q(["git","add","--",P])
r=q(["git","diff","--cached","--quiet","--",P],check=False)
if r.returncode==0: raise SystemExit(211)
q(["git","commit","-m","preserve local prediction chat wake edit before reconcile","--",P])
# Restore ONLY known diagnostic nightshift worktree dirt to local HEAD.
s=q(["git","status","--porcelain"],check=False).stdout.splitlines()
known=[]
for x in s:
 if x.strip() and not x.startswith("??") and x[3:].startswith("control/nightshift/"):
  known.append(x[3:])
if known: q(["git","restore","--",*known])
# Do not touch any remaining dirt; classify.
s=q(["git","status","--porcelain"],check=False).stdout.splitlines()
if any(x.strip() for x in s): raise SystemExit(212)
# Clean: attempt lossless rebase. Abort on conflict.
r=q(["git","rebase","origin/main"],check=False)
if r.returncode!=0:
 q(["git","rebase","--abort"],check=False)
 raise SystemExit(213)
# Success locally; deliberately do not push yet.
raise SystemExit(210)
