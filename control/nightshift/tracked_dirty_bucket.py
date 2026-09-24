#!/usr/bin/env python3
import subprocess, hashlib
from pathlib import Path
R=Path.home()/"prediction_research_prod"
p=subprocess.run(["git","status","--porcelain"],cwd=R,text=True,capture_output=True,timeout=30)
if p.returncode: raise SystemExit(60)
tracked=[x for x in p.stdout.splitlines() if x.strip() and not x.startswith("??")]
# Bucket by path families without modifying anything.
paths=[x[3:] for x in tracked]
if any(x.startswith(("control/results/","reports/","nightwork-reports/","data/","artifacts/")) for x in paths): raise SystemExit(61)
if any(x.startswith(("control/","agents/","knowledge/","tests/")) for x in paths): raise SystemExit(62)
raise SystemExit(63)
