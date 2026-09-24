#!/usr/bin/env python3
import subprocess
from pathlib import Path
R=Path.home()/"prediction_research_prod"
p=subprocess.run(["git","status","--porcelain"],cwd=R,text=True,capture_output=True,timeout=30)
ls=[x for x in p.stdout.splitlines() if x.strip()]
if not ls: raise SystemExit(220)
tracked=[x[3:] for x in ls if not x.startswith("??")]
untracked=[x[3:] for x in ls if x.startswith("??")]
# known diagnostic result created by our failed-cycle probe
if any(x=="control/results/hourly_cycle_failure_latest.json" for x in tracked): raise SystemExit(221)
if tracked:
 pth=tracked[0]
 if pth.startswith("control/tampermonkey_multichat/"): raise SystemExit(222)
 if pth.startswith("control/"): raise SystemExit(223)
 if pth.startswith("reports/"): raise SystemExit(224)
 if pth.startswith("nightwork-reports/"): raise SystemExit(225)
 raise SystemExit(226)
if untracked: raise SystemExit(227)
raise SystemExit(228)
