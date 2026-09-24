#!/usr/bin/env python3
import subprocess
from pathlib import Path
R=Path.home()/"prediction_research_prod"
p=subprocess.run(["git","status","--porcelain"],cwd=R,text=True,capture_output=True,timeout=30)
if p.returncode: raise SystemExit(70)
paths=[x[3:] for x in p.stdout.splitlines() if x.strip() and not x.startswith("??")]
# identify tracked family more narrowly
if any(x.startswith("control/nightshift/") for x in paths): raise SystemExit(71)
if any(x.startswith("control/hourly/") for x in paths): raise SystemExit(72)
if any(x.startswith("control/") for x in paths): raise SystemExit(73)
if any(x.startswith("agents/") for x in paths): raise SystemExit(74)
if any(x.startswith("knowledge/") for x in paths): raise SystemExit(75)
if any(x.startswith("tests/") for x in paths): raise SystemExit(76)
raise SystemExit(77)
