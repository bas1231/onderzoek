from __future__ import annotations
import json
import runpy
from pathlib import Path

BUS_TASK = "DEV-PRED-A2Z-SOL-R2-DIAG-EXPOSE-20261006-E010"
STATE = Path.home() / ".local/state/prediction-command-bus/tasks" / (BUS_TASK + ".json")

if STATE.is_file() and not STATE.is_symlink():
    try:
        obj = json.loads(STATE.read_text(encoding="utf-8"))
    except Exception as exc:
        print("E010_BUS_STATUS=UNREADABLE E010_BUS_REASON=" + type(exc).__name__)
    else:
        print(
            "E010_BUS_STATUS=" + str(obj.get("status"))
            + " E010_BUS_REASON=" + str(obj.get("reason"))
            + " E010_REMOTE_COMMIT=" + str(obj.get("remote_commit"))
        )
else:
    print("E010_BUS_STATUS=NO_STATE E010_BUS_REASON=NONE")

try:
    runpy.run_path("control/dev_checks/a2z_sol_r2_diag_expose_e010.py", run_name="__main__")
except SystemExit as exc:
    code = exc.code if isinstance(exc.code, int) else 10
    raise SystemExit(code)
