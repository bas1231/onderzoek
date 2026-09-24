#!/usr/bin/env python3
import subprocess
from pathlib import Path
R=Path.home()/"prediction_research_prod"
P="control/tampermonkey_multichat/prediction-chat-wake.user.js"
# Compare working tree file against HEAD and origin/main without modifying it.
def run(a):
 p=subprocess.run(a,cwd=R,text=True,capture_output=True,timeout=30)
 return p.returncode,p.stdout
rc,_=run(["git","diff","--quiet","HEAD","--",P])
if rc==0: raise SystemExit(201)
rc2,_=run(["git","diff","--quiet","origin/main","--",P])
if rc2==0: raise SystemExit(202)
# Determine whether HEAD version itself differs from origin/main.
rc3,_=run(["git","diff","--quiet","origin/main","HEAD","--",P])
if rc3==0: raise SystemExit(203) # working edit on otherwise same base
raise SystemExit(204) # working edit plus divergent committed history
