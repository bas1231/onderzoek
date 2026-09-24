#!/usr/bin/env python3
import subprocess
from pathlib import Path
R=Path.home()/"prediction_research_prod"
def o(a):
 p=subprocess.run(a,cwd=R,text=True,capture_output=True,timeout=30); return p.returncode,p.stdout.strip()
_,h=o(["git","rev-parse","HEAD"]); _,r=o(["git","rev-parse","origin/main"]); _,mb=o(["git","merge-base","HEAD","origin/main"])
# 31 local ahead, 32 local behind, 33 diverged, 34 other
if mb==r and h!=r: raise SystemExit(31)
if mb==h and h!=r: raise SystemExit(32)
if mb!=h and mb!=r: raise SystemExit(33)
raise SystemExit(34)
