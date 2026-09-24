#!/usr/bin/env python3
import subprocess
from pathlib import Path
R=Path.home()/"prediction_research_prod"
p=subprocess.run(["git","status","--porcelain"],cwd=R,text=True,capture_output=True,timeout=30)
paths=[x[3:] for x in p.stdout.splitlines() if x.strip() and not x.startswith("??") and x[3:].startswith("control/nightshift/")]
# Known diagnostics we created via sync are safe to restore from HEAD; anything else must stop.
known={"control/nightshift/hourly_cycle_failure_probe.py","control/nightshift/hourly_failure_to_git.py","control/nightshift/local_state_exitcodes.py","control/nightshift/divergence_exitcodes.py","control/nightshift/safe_reconcile_main.py","control/nightshift/dirty_state_exitcodes.py","control/nightshift/tracked_dirty_bucket.py","control/nightshift/tracked_dirty_family.py","control/nightshift/scheduler_runtime_diag.py","control/nightshift/scheduler_runtime_summary.py"}
if not paths: raise SystemExit(81)
if all(x in known for x in paths): raise SystemExit(82)
raise SystemExit(83)
