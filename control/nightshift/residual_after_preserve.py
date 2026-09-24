#!/usr/bin/env python3
import subprocess
from pathlib import Path
R=Path.home()/"prediction_research_prod"
p=subprocess.run(["git","status","--porcelain"],cwd=R,text=True,capture_output=True,timeout=30)
ls=[x for x in p.stdout.splitlines() if x.strip()]
tracked=[x[3:] for x in ls if not x.startswith("??")]
untracked=[x[3:] for x in ls if x.startswith("??")]
# Ignore newly synced diagnostic itself when classifying.
tracked=[x for x in tracked if not x.startswith("control/nightshift/")]
if tracked:
 x=tracked[0]
 if x.startswith("knowledge/"): raise SystemExit(41)
 if x.startswith("control/"): raise SystemExit(42)
 if x.startswith("agents/"): raise SystemExit(43)
 if x.startswith("tests/"): raise SystemExit(44)
 if x.startswith("reports/") or x.startswith("nightwork-reports/"): raise SystemExit(45)
 raise SystemExit(46)
if untracked:
 x=untracked[0]
 if x.startswith("control/"): raise SystemExit(47)
 if x.startswith("knowledge/"): raise SystemExit(48)
 raise SystemExit(49)
raise SystemExit(0)
