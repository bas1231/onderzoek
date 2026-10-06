from __future__ import annotations
import json
import sqlite3
import time
from pathlib import Path
import runpy

ROOT = Path.home() / ".local/share/prediction-project-executor/campaigns/FULL-A2Z-LIVE-20261004-V4"
DB = ROOT / "models" / "runtime.sqlite"
TASK_ID = "A2Z-V4-SOL-PROPOSAL-20261006-R2"

retry_at = 0.0
state = "UNKNOWN"
attempt = 0
if DB.is_file() and not DB.is_symlink():
    db = sqlite3.connect("file:" + str(DB) + "?mode=ro", uri=True)
    try:
        tr = db.execute(
            "select state,attempt,retry from transitions where task=? order by seq desc limit 1",
            (TASK_ID,),
        ).fetchone()
    finally:
        db.close()
    if tr:
        state = str(tr[0])
        attempt = int(tr[1] or 0)
        retry_at = float(tr[2] or 0.0)

now = time.time()
wait = max(0.0, retry_at - now + 5.0)
if wait > 720:
    print("R2_WAIT_CLASS=RETRY_TOO_FAR STATE=" + state + " ATTEMPT=" + str(attempt) + " RETRY_AT=" + str(retry_at))
    raise SystemExit(10)
if wait > 0:
    time.sleep(wait)

print("R2_WAIT_DONE=1 PREWAIT_STATE=" + state + " PREWAIT_ATTEMPT=" + str(attempt) + " RETRY_AT=" + str(retry_at))
runpy.run_path("control/dev_checks/a2z_sol_r2_diag_expose_e010.py", run_name="__main__")
