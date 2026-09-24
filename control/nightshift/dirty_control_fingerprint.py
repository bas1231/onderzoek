#!/usr/bin/env python3
import subprocess, hashlib
from pathlib import Path
R=Path.home()/"prediction_research_prod"
p=subprocess.run(["git","status","--porcelain"],cwd=R,text=True,capture_output=True,timeout=30)
paths=sorted(x[3:] for x in p.stdout.splitlines() if x.strip() and not x.startswith("??") and x[3:].startswith("control/") and not x[3:].startswith("control/nightshift/"))
# Encode exact path identity into a stable small bucket; no content read or modified.
if not paths: raise SystemExit(140)
h=int(hashlib.sha256("\n".join(paths).encode()).hexdigest()[:8],16)
raise SystemExit(141 + (h % 20))
