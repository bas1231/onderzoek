from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path.cwd()
TASK_ID = sys.argv[1] if len(sys.argv) > 1 else ""

subprocess.run(["git", "fetch", "origin", "main"], cwd=ROOT, check=True)
script_bytes = subprocess.run(
    ["git", "show", "origin/main:control/jobs/recover_bridge_e383.py"],
    cwd=ROOT,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    check=True,
).stdout

env = os.environ.copy()
control_path = str(ROOT / "control")
existing = env.get("PYTHONPATH", "")
env["PYTHONPATH"] = control_path if not existing else control_path + os.pathsep + existing
print("PROBE_PYTHONPATH_FIX=PASS")

with tempfile.TemporaryDirectory() as td:
    script = pathlib.Path(td) / "recover_bridge_e383.py"
    script.write_bytes(script_bytes)
    rc = subprocess.run(
        [sys.executable, str(script), TASK_ID],
        cwd=ROOT,
        env=env,
    ).returncode
    if rc != 0:
        print(f"E383_WITH_IMPORT_FIX=FAIL:{rc}")
        raise SystemExit(rc)

print("E383_WITH_IMPORT_FIX=PASS")
print("CONTROL_PLANE_RECOVER_SYNC_E385=PASS")
